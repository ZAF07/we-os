"""In-memory registry of active background runs, with a per-slug concurrency guard.

A **Run** is one execution attempt of a campaign's pipeline, identified by a unique
``run_id`` and executed as an :class:`asyncio.Task`. **At most one run per slug may
be active at a time** — the guard is keyed by slug (not thread id) because both a
full-pipeline run (``thread_id = slug``) and a single-stage run
(``thread_id = slug:stage``) write into ``campaigns/<slug>/`` and would race on the
same deliverable files.

The registry is in-memory and process-local by design: a restart means "no active
runs". A run that was live before a restart leaves its JSONL trace on disk with no
terminal ``run.summary`` — :func:`read_run_status` infers ``interrupted`` for it.
Durable run state is future work (see ``.scratch/backfill`` issue 07).
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from marketing_os.adapters.observability import find_trace, get_logger, terminal_summary
from marketing_os.config import Settings
from marketing_os.errors import RunConflictError
from marketing_os.schemas import CampaignResult

_LOGGER = get_logger("marketing_os.registry")

RUNNING = "running"
COMPLETED = "completed"
FAILED = "failed"
CANCELLED = "cancelled"
INTERRUPTED = "interrupted"

_OUTCOME_TO_STATUS = {"ok": COMPLETED, "error": FAILED, "cancelled": CANCELLED}


@dataclass(frozen=True)
class ActiveRun:
    """A live background run held in the registry.

    Attributes:
        run_id: The unique id of this execution attempt (also the trace filename).
        slug: The campaign slug the run belongs to.
        stage: The single stage being run, or ``None`` for the full pipeline.
        customer: The customer the run is for.
        task: The :class:`asyncio.Task` executing the run.
    """

    run_id: str
    slug: str
    stage: str | None
    customer: str
    task: asyncio.Task[CampaignResult]


@dataclass(frozen=True)
class RunStatus:
    """The resolved lifecycle status of a run, live or finished.

    Attributes:
        run_id: The run id queried.
        slug: The campaign slug the run belongs to.
        status: One of ``running``, ``completed``, ``failed``, ``cancelled``, or
            ``interrupted``.
        stage: The single stage the run targeted, when known.
    """

    run_id: str
    slug: str
    status: str
    stage: str | None = None


class RunRegistry:
    """Tracks active background runs keyed by slug (one active run per slug)."""

    def __init__(self) -> None:
        """Initialise an empty registry."""
        self._by_slug: dict[str, ActiveRun] = {}

    def active_for_slug(self, slug: str) -> ActiveRun | None:
        """Return the active run for a slug, or ``None`` if the slug is idle.

        Args:
            slug: The campaign slug.

        Returns:
            The slug's active run, or ``None``.
        """
        return self._by_slug.get(slug)

    def get(self, run_id: str) -> ActiveRun | None:
        """Return the active run with the given id, or ``None`` if not live.

        Args:
            run_id: The run id to look up.

        Returns:
            The matching active run, or ``None`` when no live run has that id.
        """
        for run in self._by_slug.values():
            if run.run_id == run_id:
                return run
        return None

    def active(self) -> list[ActiveRun]:
        """Return every currently active run.

        Returns:
            The live runs, one per busy slug.
        """
        return list(self._by_slug.values())

    def start(
        self,
        *,
        run_id: str,
        slug: str,
        stage: str | None,
        customer: str,
        launch: Callable[[], Coroutine[Any, Any, CampaignResult]],
    ) -> ActiveRun:
        """Register a slug's run and launch it as a background task.

        The slug is claimed synchronously before the task is scheduled, so a second
        call for the same slug is rejected even if the first run has not yet started
        executing. The run is removed from the registry when its task finishes
        (success, error, or cancellation).

        Args:
            run_id: The unique id for this run.
            slug: The campaign slug to claim.
            stage: The single stage to run, or ``None`` for the full pipeline.
            customer: The customer the run is for.
            launch: A zero-argument coroutine factory that executes the run.

        Returns:
            The registered :class:`ActiveRun`.

        Raises:
            RunConflictError: If the slug already has an active run.
        """
        existing = self._by_slug.get(slug)
        if existing is not None:
            raise RunConflictError(slug, existing.run_id)
        task = asyncio.create_task(launch())
        run = ActiveRun(run_id=run_id, slug=slug, stage=stage, customer=customer, task=task)
        self._by_slug[slug] = run
        task.add_done_callback(lambda _task: self._forget(run))
        _LOGGER.info("run.registered run_id=%s slug=%s stage=%s", run_id, slug, stage)
        return run

    def _forget(self, run: ActiveRun) -> None:
        """Drop a finished run from the registry, freeing its slug.

        Only removes the entry when it still points at ``run`` so a slug reclaimed
        by a newer run is never evicted by an older run's completion callback. A
        failed run's exception is retrieved here so asyncio does not warn that it
        was never consumed — the failure is already recorded in the run's trace as
        ``run.summary outcome=error``.

        Args:
            run: The run whose task has finished.
        """
        if self._by_slug.get(run.slug) is run:
            del self._by_slug[run.slug]
            _LOGGER.info("run.deregistered run_id=%s slug=%s", run.run_id, run.slug)
        if not run.task.cancelled():
            run.task.exception()

    async def cancel(self, run_id: str) -> ActiveRun | None:
        """Cancel a live run and wait for it to finish unwinding.

        Cancelling the task raises :class:`asyncio.CancelledError` inside the run's
        in-flight LLM call (ADR-0009), which the runner turns into a terminal
        ``run.summary outcome=cancelled`` event before the task exits. Awaiting the
        task here guarantees that terminal event and the deregistration have both
        happened before the caller returns.

        Args:
            run_id: The id of the run to cancel.

        Returns:
            The cancelled :class:`ActiveRun`, or ``None`` if no live run has that id.
        """
        run = self.get(run_id)
        if run is None:
            return None
        run.task.cancel()
        try:
            await run.task
        except asyncio.CancelledError:
            pass
        except Exception:
            pass
        return run


def read_run_status(settings: Settings, registry: RunRegistry, run_id: str) -> RunStatus | None:
    """Resolve a run's lifecycle status from the live registry, then its trace.

    A run in the registry is ``running``. Otherwise its JSONL trace is consulted:
    the terminal ``run.summary`` outcome maps to ``completed`` / ``failed`` /
    ``cancelled``; a trace with no terminal summary means the run was
    ``interrupted`` (a process-restart casualty). A run id with neither a registry
    entry nor a trace is unknown.

    Args:
        settings: The harness settings locating the ``logs/`` tree.
        registry: The live run registry.
        run_id: The run id to resolve.

    Returns:
        The resolved :class:`RunStatus`, or ``None`` when the run id is unknown.
    """
    live = registry.get(run_id)
    if live is not None:
        return RunStatus(run_id=run_id, slug=live.slug, status=RUNNING, stage=live.stage)
    trace = find_trace(settings.logs_dir, run_id)
    if trace is None:
        return None
    slug = trace.parent.name
    summary = terminal_summary(trace)
    if summary is None:
        return RunStatus(run_id=run_id, slug=slug, status=INTERRUPTED)
    status = _OUTCOME_TO_STATUS.get(str(summary.get("outcome")), INTERRUPTED)
    return RunStatus(run_id=run_id, slug=slug, status=status)


def resolve_trace_path(settings: Settings, registry: RunRegistry, run_id: str) -> Path | None:
    """Return the JSONL trace path to tail for a run, or ``None`` if unknown.

    Observing attaches by tailing this file. A **live** run's path is derived from
    its slug even when the file does not exist yet — the task may not have written
    its first event — so a client attaching immediately after ``POST /run`` is not
    turned away with a spurious 404; the tailer waits for the file to appear. A run
    that is no longer live is located by its on-disk trace. A run id that is neither
    live nor traced is unknown.

    Args:
        settings: The harness settings locating the ``logs/`` tree.
        registry: The live run registry.
        run_id: The run id to resolve a trace path for.

    Returns:
        The trace path to tail, or ``None`` when the run id is unknown.
    """
    live = registry.get(run_id)
    if live is not None:
        return settings.logs_dir / live.slug / f"{run_id}.jsonl"
    return find_trace(settings.logs_dir, run_id)

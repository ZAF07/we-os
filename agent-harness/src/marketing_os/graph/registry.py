"""Registry of background runs, over a durable run store.

A **Run** is one execution attempt of a campaign's pipeline, identified by a
unique ``run_id`` and executed as an :class:`asyncio.Task`. **One campaign is
run by one person at a time.** The guard is a claim on ``(tenant, slug)``, not
on a thread id, because a full-pipeline run and a single-stage run of the same
campaign both write into ``campaigns/<slug>/`` and would race on the same
deliverable documents. The claim names the person who took it, so a colleague in
the same business is refused too — and told that is why.

The registry has two halves. The :class:`~marketing_os.ports.RunStore` holds the
claim and the lifecycle status **durably**, so both outlive the process; the
:class:`asyncio.Task` lives only in this process, since only the running process
can abort its own in-flight LLM call.

Two consequences follow, and both are behaviour a reviewer should look for:

- **Abandoning is explicit.** A cancelled run's campaign has its checkpoint
  threads cleared (:func:`~marketing_os.graph.checkpoints.clear_campaign_threads`).
  Under an ephemeral checkpointer that was free; under a durable one, omitting it
  turns "a cancelled run starts clean" into "resume from the last checkpoint".
- **Runs a crash left behind are resolved, not lost.** On startup every run still
  marked ``running`` is resolved as ``interrupted``, because the service is a
  single process: nothing else could be executing it. Running two copies would
  therefore break this, which is why single-process is an assumption of the
  design rather than a deployment preference (ADR-0025).
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver

from marketing_os.adapters.observability import find_trace, get_logger, terminal_summary
from marketing_os.adapters.runs import (
    CANCELLED,
    COMPLETED,
    FAILED,
    INTERRUPTED,
    RUNNING,
    InMemoryRunStore,
)
from marketing_os.config import Settings
from marketing_os.graph.checkpoints import clear_campaign_threads
from marketing_os.ports import RunStore
from marketing_os.schemas import CampaignResult, RunRecord

_LOGGER = get_logger("marketing_os.registry")

_OUTCOME_TO_STATUS = {"ok": COMPLETED, "error": FAILED, "cancelled": CANCELLED}


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
    """Claims campaigns in a shared store and executes the claimed runs locally."""

    def __init__(
        self,
        store: RunStore | None = None,
        *,
        checkpointer: BaseCheckpointSaver | None = None,
    ) -> None:
        """Initialise the registry.

        Args:
            store: The run store holding claims and statuses; defaults to a
                process-local :class:`~marketing_os.adapters.runs.InMemoryRunStore`.
            checkpointer: The checkpointer whose threads are cleared when a run
                is abandoned, or ``None`` when the deployment runs without one.
        """
        self._store: RunStore = store or InMemoryRunStore()
        self._checkpointer = checkpointer
        self._tasks: dict[str, asyncio.Task[CampaignResult]] = {}

    def task_for(self, run_id: str) -> asyncio.Task[CampaignResult] | None:
        """Return the task executing a run, if it is still in flight.

        Args:
            run_id: The run id to look up.

        Returns:
            The executing task, or ``None`` once the run has finished.
        """
        return self._tasks.get(run_id)

    def active_for_campaign(self, tenant: str, slug: str) -> RunRecord | None:
        """Return the run holding a campaign's claim, or ``None`` if it is idle.

        Args:
            tenant: The tenant that owns the campaign.
            slug: The campaign slug.

        Returns:
            The claiming record, or ``None``.
        """
        return self._store.active_for_campaign(tenant, slug)

    def for_campaign(self, tenant: str, slug: str) -> list[RunRecord]:
        """Return every run recorded for a campaign, newest first.

        Args:
            tenant: The tenant that owns the campaign.
            slug: The campaign slug.

        Returns:
            The campaign's runs, whatever their status.
        """
        return self._store.for_campaign(tenant, slug)

    def get(self, run_id: str, tenant: str) -> RunRecord | None:
        """Return a tenant's run with the given id, whatever its status.

        The tenant is part of the lookup rather than a filter applied to the
        result, so there is no unscoped call shape for new code to reach for. A
        run belonging to another tenant is reported as absent, not refused, so
        the two cases stay indistinguishable (ADR-0013).

        Args:
            run_id: The run id to look up.
            tenant: The tenant the caller acts for.

        Returns:
            The matching record, or ``None`` when no run has that id **or** it
            belongs to another tenant.
        """
        return self._store.get(run_id, tenant)

    def active(self, tenant: str) -> list[RunRecord]:
        """Return one tenant's currently running runs.

        Args:
            tenant: The tenant whose runs to list.

        Returns:
            The tenant's live runs, one per busy campaign. Other tenants' runs
            are never returned, so a caller cannot forget to exclude them.
        """
        return self._store.active(tenant)

    def is_live(self, run_id: str, tenant: str) -> bool:
        """Return whether a tenant's run is still executing.

        Used only to decide when a trace stream may stop polling; the caller has
        already proved it owns the run by resolving its trace path.

        Args:
            run_id: The run id to test.
            tenant: The tenant the caller acts for.

        Returns:
            ``True`` while that run is executing.
        """
        record = self._store.get(run_id, tenant)
        return record is not None and record.status == RUNNING

    def start(
        self,
        *,
        run_id: str,
        slug: str,
        stage: str | None,
        tenant: str,
        user_id: str = "",
        launch: Callable[[], Coroutine[Any, Any, CampaignResult]],
    ) -> RunRecord:
        """Claim a campaign in the shared store and launch its run as a background task.

        The claim is taken synchronously, and durably, before the task is
        scheduled: a second call for the same campaign is rejected even if the
        first run has not started executing, and whether it comes from the same
        person or a colleague. The claim is released when the task finishes
        (success, error, or cancellation).

        Args:
            run_id: The unique id for this run.
            slug: The campaign slug to claim.
            stage: The single stage to run, or ``None`` for the full pipeline.
            tenant: The tenant the run is for.
            user_id: The person starting the run, who becomes the only one who
                may cancel it while it is in flight.
            launch: A zero-argument coroutine factory that executes the run.

        Returns:
            The claimed :class:`~marketing_os.schemas.RunRecord`.

        Raises:
            RunConflictError: If the campaign already has an active run.
        """
        record = self._store.claim(
            RunRecord(
                run_id=run_id,
                tenant_id=tenant,
                slug=slug,
                stage=stage,
                user_id=user_id,
                status=RUNNING,
                started_at=time.time(),
            )
        )
        task = asyncio.create_task(launch())
        self._tasks[run_id] = task
        task.add_done_callback(lambda finished: self._forget(record, finished))
        _LOGGER.info("run.registered run_id=%s slug=%s stage=%s", run_id, slug, stage)
        return record

    def _forget(self, record: RunRecord, task: asyncio.Task[CampaignResult]) -> None:
        """Resolve a finished run in the store and drop its local task.

        The store keeps whatever terminal status it already holds, so a run
        cancelled or reclaimed elsewhere is not overwritten by this callback. A
        failed run's exception is retrieved here so asyncio does not warn that it
        was never consumed — the failure is already recorded in the run's trace
        as ``run.summary outcome=error``.

        Args:
            record: The run whose task has finished.
            task: The finished task.
        """
        self._tasks.pop(record.run_id, None)
        if task.cancelled():
            status = CANCELLED
        elif task.exception() is not None:
            status = FAILED
        else:
            status = COMPLETED
        self._store.finish(record.run_id, status)
        _LOGGER.info(
            "run.deregistered run_id=%s slug=%s status=%s", record.run_id, record.slug, status
        )

    async def cancel(self, run_id: str, tenant: str, user_id: str = "") -> RunRecord | None:
        """Cancel a live run, abandon its checkpoints, and wait for it to unwind.

        Cancelling the task raises :class:`asyncio.CancelledError` inside the run's
        in-flight LLM call (ADR-0009), which the runner turns into a terminal
        ``run.summary outcome=cancelled`` event before the task exits. Awaiting the
        task here guarantees that terminal event and the deregistration have both
        happened before the caller returns.

        The order matters twice over. The claim is released **last** — after the
        task has unwound *and* after the campaign's checkpoint threads are
        cleared — so no new run of the campaign can start while the cancelled one
        is still writing to it, and none can start on a thread this cancel is
        about to delete. Clearing the threads is what makes that next run begin
        at stage 1 rather than resuming the work just cancelled.

        Args:
            run_id: The id of the run to cancel.
            tenant: The tenant the caller acts for. A run belonging to another
                tenant is treated as absent, so one business can never cancel
                another's work.
            user_id: The person cancelling. A run started by a colleague is
                treated as absent rather than refused, so cancelling stays the
                privilege of whoever is driving the campaign.

        Returns:
            The cancelled record, or ``None`` if the caller has no live run with
            that id — because it does not exist, belongs to another business, or
            belongs to a colleague.
        """
        record = self._store.get(run_id, tenant)
        if record is None or record.status != RUNNING:
            return None
        if record.user_id and record.user_id != user_id:
            return None
        task = self._tasks.get(run_id)
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
        await clear_campaign_threads(self._checkpointer, record.tenant_id, record.slug)
        self._store.finish(run_id, CANCELLED)
        return record

    async def reclaim_abandoned(self) -> list[RunRecord]:
        """Resolve every run a previous process died holding, and clear its state.

        Called on startup. A run still marked ``running`` when this process
        starts cannot be executing — the service is a single process — so it is
        one a crash or a deploy left behind, and it is resolved as
        ``interrupted`` rather than staying ``running`` forever. Each reclaimed
        campaign has its checkpoint threads cleared for the same reason a
        cancelled one does: the run is abandoned, so its next start must be clean
        rather than a silent resume of half-finished work.

        Returns:
            The records that were reclaimed.
        """
        reclaimed = self._store.reclaim_running(INTERRUPTED)
        for record in reclaimed:
            await clear_campaign_threads(self._checkpointer, record.tenant_id, record.slug)
            _LOGGER.info("run.reclaimed run_id=%s slug=%s", record.run_id, record.slug)
        return reclaimed


def read_run_status(
    settings: Settings, registry: RunRegistry, run_id: str, tenant: str
) -> RunStatus | None:
    """Resolve a run's lifecycle status from the shared run store, then its trace.

    The store is authoritative: it records ``running`` while the campaign is
    claimed, and the terminal status when the run resolves — including the
    ``interrupted`` a restart assigns to runs a crash left behind. Runs predating
    the store fall back to the JSONL trace, where the terminal ``run.summary``
    outcome maps to
    ``completed`` / ``failed`` / ``cancelled`` and a trace with no terminal
    summary means ``interrupted``. A run id with neither a record nor a trace
    **within the caller's tenant** is unknown.

    Args:
        settings: The harness settings locating the ``logs/`` tree.
        registry: The run registry fronting the run store.
        run_id: The run id to resolve.
        tenant: The tenant the caller acts for; runs outside it are unknown.

    Returns:
        The resolved :class:`RunStatus`, or ``None`` when the run id is unknown.
    """
    record = registry.get(run_id, tenant)
    if record is not None:
        return RunStatus(run_id=run_id, slug=record.slug, status=record.status, stage=record.stage)
    trace = find_trace(settings.tenant_logs_dir(tenant), run_id)
    if trace is None:
        return None
    slug = trace.parent.name
    summary = terminal_summary(trace)
    if summary is None:
        return RunStatus(run_id=run_id, slug=slug, status=INTERRUPTED)
    status = _OUTCOME_TO_STATUS.get(str(summary.get("outcome")), INTERRUPTED)
    return RunStatus(run_id=run_id, slug=slug, status=status)


def resolve_trace_path(
    settings: Settings, registry: RunRegistry, run_id: str, tenant: str
) -> Path | None:
    """Return the JSONL trace path to tail for a run, or ``None`` if unknown.

    Observing attaches by tailing this file. A **live** run's path is derived from
    its slug even when the file does not exist yet — the task may not have written
    its first event — so a client attaching immediately after ``POST /run`` is not
    turned away with a spurious 404; the tailer waits for the file to appear. A run
    that is no longer live is located by its on-disk trace. A run id that is neither
    recorded nor traced within the caller's tenant is unknown.

    Args:
        settings: The harness settings locating the ``logs/`` tree.
        registry: The run registry fronting the run store.
        run_id: The run id to resolve a trace path for.
        tenant: The tenant the caller acts for; runs outside it are unknown.

    Returns:
        The trace path to tail, or ``None`` when the run id is unknown.
    """
    record = registry.get(run_id, tenant)
    if record is not None:
        return settings.tenant_logs_dir(tenant) / record.slug / f"{run_id}.jsonl"
    return find_trace(settings.tenant_logs_dir(tenant), run_id)

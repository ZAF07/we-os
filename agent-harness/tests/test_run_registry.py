"""Run registry: per-slug concurrency guard, cancellation, and status inference.

These exercise the in-memory :class:`RunRegistry` directly (no HTTP). The
concurrency guard is proven with launches that block on an event the test
controls, so "one active run per slug" is deterministic. Cancellation is proven
end-to-end against the real async runner with a :class:`BlockingChatModel`, so the
in-flight LLM call is genuinely aborted and the trace ends with a terminal
``run.summary outcome=cancelled``. Status inference reads hand-written traces so
each of the five states maps deterministically.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from conftest import BlockingChatModel, install_scripted_graph
from marketing_os.adapters.observability import new_run_id
from marketing_os.config import Settings
from marketing_os.errors import RunConflictError
from marketing_os.graph.registry import RunRegistry, read_run_status
from marketing_os.graph.runner import arun_campaign
from marketing_os.schemas import CampaignResult


def _blocking_launch(gate: asyncio.Event, slug: str) -> Any:
    """Return a launch coroutine factory that blocks until ``gate`` is set.

    Args:
        gate: The event the launched run waits on before completing.
        slug: The slug to stamp on the returned result.

    Returns:
        A zero-argument coroutine factory suitable for :meth:`RunRegistry.start`.
    """

    async def launch() -> CampaignResult:
        """Block on the gate, then return a trivial result.

        Returns:
            A minimal campaign result.
        """
        await gate.wait()
        return CampaignResult(customer="acme", slug=slug)

    return launch


async def _drain(gate: asyncio.Event, registry: RunRegistry) -> None:
    """Release every blocked run and let the event loop retire their tasks.

    Args:
        gate: The gate the blocked launches wait on.
        registry: The registry whose tasks should be drained.
    """
    gate.set()
    for run in registry.active():
        await run.task


async def test_start_rejects_second_run_for_same_slug() -> None:
    gate = asyncio.Event()
    registry = RunRegistry()
    first_id = new_run_id()
    registry.start(
        run_id=first_id,
        slug="acme",
        stage=None,
        customer="acme",
        launch=_blocking_launch(gate, "acme"),
    )

    with pytest.raises(RunConflictError) as excinfo:
        registry.start(
            run_id=new_run_id(),
            slug="acme",
            stage=None,
            customer="acme",
            launch=_blocking_launch(gate, "acme"),
        )

    assert excinfo.value.active_run_id == first_id
    active = registry.active_for_slug("acme")
    assert active is not None
    assert active.run_id == first_id
    await _drain(gate, registry)


async def test_full_and_single_stage_runs_share_the_slug_guard() -> None:
    gate = asyncio.Event()
    registry = RunRegistry()
    registry.start(
        run_id=new_run_id(),
        slug="acme",
        stage=None,
        customer="acme",
        launch=_blocking_launch(gate, "acme"),
    )

    with pytest.raises(RunConflictError):
        registry.start(
            run_id=new_run_id(),
            slug="acme",
            stage="research",
            customer="acme",
            launch=_blocking_launch(gate, "acme"),
        )

    await _drain(gate, registry)


async def test_different_slugs_run_concurrently() -> None:
    gate = asyncio.Event()
    registry = RunRegistry()
    registry.start(
        run_id=new_run_id(),
        slug="acme",
        stage=None,
        customer="acme",
        launch=_blocking_launch(gate, "acme"),
    )
    registry.start(
        run_id=new_run_id(),
        slug="beta",
        stage=None,
        customer="acme",
        launch=_blocking_launch(gate, "beta"),
    )

    assert {run.slug for run in registry.active()} == {"acme", "beta"}
    await _drain(gate, registry)


async def test_completed_run_frees_its_slug() -> None:
    gate = asyncio.Event()
    gate.set()
    registry = RunRegistry()
    run = registry.start(
        run_id=new_run_id(),
        slug="acme",
        stage=None,
        customer="acme",
        launch=_blocking_launch(gate, "acme"),
    )

    await run.task

    assert registry.active_for_slug("acme") is None
    assert registry.get(run.run_id) is None
    registry.start(
        run_id=new_run_id(),
        slug="acme",
        stage=None,
        customer="acme",
        launch=_blocking_launch(gate, "acme"),
    )
    await _drain(gate, registry)


async def test_cancel_aborts_in_flight_call_writes_cancelled_summary_and_deregisters(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = BlockingChatModel()
    install_scripted_graph(monkeypatch, model_factory=lambda: model)
    registry = RunRegistry()
    run_id = new_run_id()

    async def launch() -> CampaignResult:
        """Run the research stage on the real async path with the blocking model.

        Returns:
            The structured campaign result (never reached; the run is cancelled).
        """
        return await arun_campaign(settings, "acme", "acme", stage="research", run_id=run_id)

    registry.start(run_id=run_id, slug="acme", stage="research", customer="acme", launch=launch)
    await asyncio.wait_for(model.entered.wait(), timeout=5)

    cancelled = await registry.cancel(run_id)

    assert cancelled is not None
    assert model.was_cancelled is True, "the in-flight LLM call was not aborted"
    assert registry.get(run_id) is None
    assert registry.active_for_slug("acme") is None

    trace = settings.logs_dir / "acme" / f"{run_id}.jsonl"
    events = [json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines() if line]
    summaries = [event for event in events if event.get("event") == "run.summary"]
    assert summaries and summaries[-1]["outcome"] == "cancelled"
    assert not (settings.campaigns_dir / "acme" / "research.md").is_file()


async def test_cancel_unknown_run_returns_none() -> None:
    registry = RunRegistry()
    assert await registry.cancel("does-not-exist") is None


async def test_status_is_running_for_a_live_run(settings: Settings) -> None:
    gate = asyncio.Event()
    registry = RunRegistry()
    run_id = new_run_id()
    registry.start(
        run_id=run_id,
        slug="acme",
        stage=None,
        customer="acme",
        launch=_blocking_launch(gate, "acme"),
    )

    status = read_run_status(settings, registry, run_id)

    assert status is not None
    assert status.status == "running"
    assert status.slug == "acme"
    await _drain(gate, registry)


def _write_trace(settings: Settings, slug: str, run_id: str, events: list[dict]) -> None:
    """Write a JSONL trace with the given events under ``logs/<slug>/``.

    Args:
        settings: The harness settings locating the logs tree.
        slug: The campaign slug the trace belongs to.
        run_id: The run id (trace filename without extension).
        events: The event dicts to serialise, one per line.
    """
    path = settings.logs_dir / slug / f"{run_id}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")


@pytest.mark.parametrize(
    ("outcome", "expected"),
    [("ok", "completed"), ("error", "failed"), ("cancelled", "cancelled")],
)
def test_status_maps_terminal_outcome(settings: Settings, outcome: str, expected: str) -> None:
    run_id = new_run_id()
    _write_trace(
        settings,
        "acme",
        run_id,
        [
            {"event": "stage.start", "stage": "research"},
            {"event": "run.summary", "outcome": outcome},
        ],
    )
    status = read_run_status(settings, RunRegistry(), run_id)
    assert status is not None
    assert status.status == expected
    assert status.slug == "acme"


def test_status_is_interrupted_when_trace_has_no_summary(settings: Settings) -> None:
    run_id = new_run_id()
    _write_trace(settings, "acme", run_id, [{"event": "stage.start", "stage": "research"}])
    status = read_run_status(settings, RunRegistry(), run_id)
    assert status is not None
    assert status.status == "interrupted"


def test_status_is_none_for_unknown_run(settings: Settings) -> None:
    assert read_run_status(settings, RunRegistry(), "no-such-run") is None

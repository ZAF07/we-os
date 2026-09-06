"""Abandonment: cancelling and crashing must not leave resumable state behind.

The trap this file exists for: once checkpoints are durable, resuming is the
default. A cancelled run whose checkpoint threads survive silently turns "a
cancelled run starts clean" into "resume from the last checkpoint" — which
passes review and breaks in production, because the owner cancelled precisely to
stop that work.

The observable is the **stage list the restarted run reports**. ``results`` is an
accumulating channel, so a checkpoint that survives cancellation carries the
cancelled run's completed stages into the next run: the restarted run reports
stages it never executed, and the pipeline effectively picks up where the
cancelled one left off. A run that starts clean reports each stage exactly once,
in pipeline order. That is readable from the run's own trace, with no reach into
graph internals.
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.checkpoint.base import empty_checkpoint
from langgraph.checkpoint.memory import MemorySaver
from pydantic import Field

from conftest import (
    OTHER_TENANT,
    SLUG,
    TENANT,
    authenticate,
    deliverable_from,
    install_prototype_adapters,
    install_scripted_graph,
    run_without_approval_gates,
    write_all_agent_specs,
    write_call,
)
from marketing_os.adapters.observability import new_run_id
from marketing_os.adapters.runs import InMemoryRunStore
from marketing_os.config import Settings
from marketing_os.errors import RunConflictError
from marketing_os.governance.pipeline import PIPELINE
from marketing_os.graph.checkpoints import clear_campaign_threads, thread_id
from marketing_os.graph.registry import RunRegistry, read_run_status
from marketing_os.schemas import CampaignResult, RunRecord

"""One campaign is run by one person at a time, so the fixtures need two people
in the same business — the colleague is the case the guard exists for."""

USER = "usr_owner"
COLLEAGUE = "usr_colleague"


def _client(repo: Path) -> TestClient:
    """Build a hermetic API client bound to the temp repo, acting as the tenant.

    Args:
        repo: The hermetic repository root fixture.

    Returns:
        A configured (not yet entered) test client.
    """
    from marketing_os.entrypoints.api.app import app, get_settings

    get_settings.cache_clear()
    install_prototype_adapters(repo)
    authenticate(app)
    return TestClient(app)


def _trace_events(settings: Settings, run_id: str) -> list[dict]:
    """Read a run's JSONL trace.

    Args:
        settings: The harness settings locating the logs tree.
        run_id: The run whose trace to read.

    Returns:
        The trace's events in order.
    """
    path = settings.tenant_logs_dir(TENANT) / SLUG / f"{run_id}.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line]


def _stages_reported(settings: Settings, run_id: str) -> list[str]:
    """Return the stages a finished run claimed in its terminal summary.

    Args:
        settings: The harness settings locating the logs tree.
        run_id: The finished run's id.

    Returns:
        The stage keys the run reported, in the order it reported them.
    """
    summaries = [e for e in _trace_events(settings, run_id) if e["event"] == "run.summary"]
    assert summaries, f"run {run_id} wrote no terminal summary"
    return [result["stage"] for result in summaries[-1]["results"]]


def _stages_executed(settings: Settings, run_id: str) -> list[str]:
    """Return the stages a run actually executed, in order.

    Args:
        settings: The harness settings locating the logs tree.
        run_id: The run's id.

    Returns:
        The stage keys the run emitted a ``stage.start`` for.
    """
    return [e["stage"] for e in _trace_events(settings, run_id) if e["event"] == "stage.start"]


def _wait_for_status(client: TestClient, run_id: str, target: str) -> None:
    """Poll a run's status until it reaches ``target``.

    Args:
        client: The entered test client.
        run_id: The run id to poll.
        target: The status to wait for.

    Raises:
        AssertionError: If the run never reaches the target status.
    """
    for _ in range(200):
        if client.get(f"/runs/{run_id}").json().get("status") == target:
            return
        time.sleep(0.02)
    raise AssertionError(f"run {run_id} never reached status {target!r}")


# --- The trap: a cancelled run must not be resumable ----------------------------


class WriteFirstStageThenBlock(BaseChatModel):
    """Completes the research stage, then blocks forever inside the next one.

    This puts a run in the state the trap needs: stage 1 finished and recorded in
    the checkpoint, stage 2 in flight and cancellable. A model that blocked
    immediately would leave nothing worth resuming, so the bug would not show.
    """

    reached_second_stage: asyncio.Event = Field(default_factory=asyncio.Event)
    model_config = {"arbitrary_types_allowed": True}

    @property
    def _llm_type(self) -> str:
        """Return the model type identifier."""
        return "write-first-stage-then-block"

    def bind_tools(self, tools: Any, **kwargs: Any) -> WriteFirstStageThenBlock:
        """Ignore tool binding and return self, since replies are scripted.

        Args:
            tools: The tools being bound (ignored).
            **kwargs: Additional binding arguments (ignored).

        Returns:
            This model instance.
        """
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Fail loudly if invoked synchronously; this model is async-only.

        Args:
            messages: The conversation so far (unused).
            stop: Stop sequences (ignored).
            run_manager: The callback manager (ignored).
            **kwargs: Additional arguments (ignored).

        Raises:
            NotImplementedError: Always, to prove the async path is exercised.
        """
        raise NotImplementedError("this model is async-only")

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Write the research deliverable; block on any later stage.

        Args:
            messages: The conversation so far.
            stop: Stop sequences (ignored).
            run_manager: The callback manager (ignored).
            **kwargs: Additional arguments (ignored).

        Returns:
            The scripted reply for the research stage.
        """
        if isinstance(messages[-1], ToolMessage):
            return ChatResult(generations=[ChatGeneration(message=AIMessage("Saved. Done."))])
        path = deliverable_from(messages)
        if path.endswith("research.md"):
            message = write_call(path, f"# Deliverable\n\nContent for {path}.")
            return ChatResult(generations=[ChatGeneration(message=message)])
        self.reached_second_stage.set()
        await asyncio.Event().wait()
        raise AssertionError("unreachable")


def test_a_cancelled_run_restarts_from_stage_one_rather_than_resuming(
    repo: Path, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cancel after stage 1, start again, and the pipeline runs every stage itself.

    Both runs share one process-wide checkpointer — that is the whole point:
    with an ephemeral one this could not regress, and with a durable one it
    regresses the moment cancellation stops clearing threads. Were the cancelled
    run's checkpoint left behind, the restarted run would report research as
    done without running it, having inherited it through the accumulating
    ``results`` channel.
    """
    monkeypatch.setenv("MARKETING_OS_ROOT", str(repo))
    run_without_approval_gates(monkeypatch)
    write_all_agent_specs(settings)
    blocking = WriteFirstStageThenBlock()
    install_scripted_graph(monkeypatch, model_factory=lambda: blocking)

    with _client(repo) as client:
        cancelled_id = client.post(f"/campaigns/{SLUG}/run", json={}).json()["run_id"]
        for _ in range(200):
            if blocking.reached_second_stage.is_set():
                break
            time.sleep(0.02)
        assert blocking.reached_second_stage.is_set(), "the first run never got past stage 1"
        assert client.post(f"/runs/{cancelled_id}/cancel").status_code == 200

        install_scripted_graph(monkeypatch)
        restarted_id = client.post(f"/campaigns/{SLUG}/run", json={}).json()["run_id"]
        _wait_for_status(client, restarted_id, "completed")

    expected = [stage.key for stage in PIPELINE]
    assert _stages_reported(settings, restarted_id) == expected
    assert _stages_executed(settings, restarted_id) == expected


def _save_checkpoint(saver: MemorySaver, thread: str) -> None:
    """Write one checkpoint under a thread id, standing in for a run's saved state.

    Args:
        saver: The checkpointer to write into.
        thread: The thread id to save under.
    """
    saver.put(
        {"configurable": {"thread_id": thread, "checkpoint_ns": ""}},
        empty_checkpoint(),
        {},
        {},
    )


def _has_state(saver: MemorySaver, thread: str) -> bool:
    """Return whether a thread still holds checkpointed state.

    Args:
        saver: The checkpointer to query.
        thread: The thread id to check.

    Returns:
        ``True`` while the thread has a checkpoint.
    """
    return saver.get_tuple({"configurable": {"thread_id": thread}}) is not None


async def test_cancelling_clears_the_full_pipeline_and_every_per_stage_thread() -> None:
    """A single-stage run checkpoints under its own thread, so both kinds must go."""
    saver = MemorySaver()
    full = thread_id(TENANT, SLUG, None)
    single = thread_id(TENANT, SLUG, "research")
    _save_checkpoint(saver, full)
    _save_checkpoint(saver, single)

    cleared = await clear_campaign_threads(saver, TENANT, SLUG)

    assert full in cleared and single in cleared
    assert not _has_state(saver, full)
    assert not _has_state(saver, single)


async def test_clearing_one_tenants_campaign_leaves_another_tenants_alone() -> None:
    """Two businesses may pick the same slug; one cancelling must not wipe the other."""
    saver = MemorySaver()
    theirs = thread_id(OTHER_TENANT, SLUG, "research")
    _save_checkpoint(saver, theirs)

    await clear_campaign_threads(saver, TENANT, SLUG)

    assert _has_state(saver, theirs)


# --- Surviving a restart --------------------------------------------------------


def _launch_forever() -> object:
    """Return a launch factory whose run never finishes on its own.

    Returns:
        A zero-argument coroutine factory suitable for :meth:`RunRegistry.start`.
    """

    async def launch() -> CampaignResult:
        """Block indefinitely, standing in for a run in progress.

        Returns:
            A campaign result (never reached).
        """
        await asyncio.Event().wait()
        return CampaignResult(tenant=TENANT, slug=SLUG)

    return launch


async def test_a_restart_resolves_runs_the_previous_process_died_holding(
    settings: Settings,
) -> None:
    """A crash must leave a terminal status, not a run stuck ``running`` forever."""
    store = InMemoryRunStore()
    crashed = RunRegistry(store)
    run_id = new_run_id()
    crashed.start(
        run_id=run_id, slug=SLUG, stage=None, tenant=TENANT, user_id=USER, launch=_launch_forever()
    )

    restarted = RunRegistry(store)
    reclaimed = await restarted.reclaim_abandoned()

    assert [record.run_id for record in reclaimed] == [run_id]
    status = read_run_status(settings, restarted, run_id, TENANT)
    assert status is not None
    assert status.status == "interrupted"
    assert restarted.active_for_campaign(TENANT, SLUG) is None

    task = crashed.task_for(run_id)
    assert task is not None
    task.cancel()


async def test_a_restart_leaves_finished_runs_alone() -> None:
    """Only runs still marked running are swept; history is not rewritten."""
    store = InMemoryRunStore()
    registry = RunRegistry(store)
    finished = new_run_id()
    store.claim(RunRecord(run_id=finished, tenant_id=TENANT, slug="other", user_id=USER))
    store.finish(finished, "completed")

    reclaimed = await registry.reclaim_abandoned()

    assert reclaimed == []
    record = registry.get(finished, TENANT)
    assert record is not None and record.status == "completed"


# --- One campaign is run by one person at a time --------------------------------


async def test_a_colleague_cannot_start_a_run_on_a_campaign_someone_else_is_running() -> None:
    """Two people driving one campaign would overwrite each other's deliverables."""
    registry = RunRegistry(InMemoryRunStore())
    held = new_run_id()
    registry.start(
        run_id=held, slug=SLUG, stage=None, tenant=TENANT, user_id=USER, launch=_launch_forever()
    )

    with pytest.raises(RunConflictError) as refused:
        registry.start(
            run_id=new_run_id(),
            slug=SLUG,
            stage="research",
            tenant=TENANT,
            user_id=COLLEAGUE,
            launch=_launch_forever(),
        )

    assert refused.value.active_run_id == held
    assert refused.value.active_user_id == USER
    assert "someone else in your business" in str(refused.value)

    task = registry.task_for(held)
    assert task is not None
    task.cancel()


async def test_a_colleague_cannot_cancel_a_run_they_did_not_start() -> None:
    """A run belongs to whoever started it, for as long as it is in flight."""
    registry = RunRegistry(InMemoryRunStore())
    run_id = new_run_id()
    registry.start(
        run_id=run_id, slug=SLUG, stage=None, tenant=TENANT, user_id=USER, launch=_launch_forever()
    )

    assert await registry.cancel(run_id, TENANT, COLLEAGUE) is None
    still_running = registry.get(run_id, TENANT)
    assert still_running is not None and still_running.status == "running"

    task = registry.task_for(run_id)
    assert task is not None
    task.cancel()


async def test_the_person_who_started_a_run_can_cancel_it() -> None:
    registry = RunRegistry(InMemoryRunStore())
    run_id = new_run_id()
    registry.start(
        run_id=run_id, slug=SLUG, stage=None, tenant=TENANT, user_id=USER, launch=_launch_forever()
    )

    cancelled = await registry.cancel(run_id, TENANT, USER)

    assert cancelled is not None
    assert registry.active_for_campaign(TENANT, SLUG) is None


async def test_a_campaign_is_claimable_again_once_its_run_finishes() -> None:
    """The lock is on the active run, not on the campaign forever."""
    registry = RunRegistry(InMemoryRunStore())
    first = new_run_id()
    registry.start(
        run_id=first, slug=SLUG, stage=None, tenant=TENANT, user_id=USER, launch=_launch_forever()
    )
    task = registry.task_for(first)
    assert task is not None
    task.cancel()
    await registry.cancel(first, TENANT, USER)

    registry.start(
        run_id=new_run_id(),
        slug=SLUG,
        stage=None,
        tenant=TENANT,
        user_id=COLLEAGUE,
        launch=_launch_forever(),
    )

    held = registry.active_for_campaign(TENANT, SLUG)
    assert held is not None and held.user_id == COLLEAGUE
    running = registry.task_for(held.run_id)
    if running is not None:
        running.cancel()


async def test_two_tenants_may_run_the_same_slug_at_the_same_time() -> None:
    """Slugs are chosen by businesses, so the guard is per campaign, not per name."""
    registry = RunRegistry(InMemoryRunStore())
    mine = new_run_id()
    theirs = new_run_id()

    registry.start(
        run_id=mine, slug=SLUG, stage=None, tenant=TENANT, user_id=USER, launch=_launch_forever()
    )
    registry.start(
        run_id=theirs,
        slug=SLUG,
        stage=None,
        tenant=OTHER_TENANT,
        user_id=USER,
        launch=_launch_forever(),
    )

    assert [record.run_id for record in registry.active(TENANT)] == [mine]
    assert [record.run_id for record in registry.active(OTHER_TENANT)] == [theirs]

    for run_id in (mine, theirs):
        task = registry.task_for(run_id)
        assert task is not None
        task.cancel()

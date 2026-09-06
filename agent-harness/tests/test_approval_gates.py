"""Approval Gates: the run stops and asks, and revisions append rather than overwrite.

This is the feature that makes we-OS a decision-making system rather than a
generator (ADR-0015). What is pinned here is the end-to-end behaviour a business
owner sees: the run works through research on its own, halts at brand strategy,
and goes no further until a person says yes — and when they say "not this", the
re-run produces a **new version** with the prior one still readable.

The graph-level tests drive the compiled graph directly so the interrupt and the
resume are observable without HTTP; the API tests prove the same behaviour
through the endpoints a frontend calls. Both use scripted models and fake
reviewers, so nothing here touches a network.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from conftest import (
    PASS_VERDICT,
    SLUG,
    TENANT,
    FakeReviewer,
    ProgrammableChatModel,
    authenticate,
    clear_prototype_adapters,
    deliverable_from,
    install_prototype_adapters,
    install_scripted_graph,
    with_prototype_defaults,
    write_all_agent_specs,
    write_call,
)
from marketing_os.adapters.deliverables import InMemoryDeliverableStore
from marketing_os.config import Settings
from marketing_os.graph.graph import build_campaign_graph as _build_campaign_graph
from marketing_os.graph.runner import awaiting_approval_stage
from marketing_os.questionnaire import SEED_QUESTIONNAIRE


def build_campaign_graph(settings: Settings, **kwargs: Any) -> Any:
    """Build the full campaign graph against the seed question set and the hermetic repo.

    Args:
        settings: The harness settings.
        **kwargs: The builder's remaining keyword arguments.

    Returns:
        The compiled campaign graph.
    """
    kwargs.setdefault("questionnaire", SEED_QUESTIONNAIRE)
    with_prototype_defaults(settings, kwargs)
    return _build_campaign_graph(settings, **kwargs)


def _config(thread: str) -> dict:
    """Build an invoke config with a thread id and a generous recursion limit.

    Args:
        thread: The checkpoint thread id.

    Returns:
        The runnable config.
    """
    return {"configurable": {"thread_id": thread}, "recursion_limit": 60}


def _numbered_handler(messages: list[BaseMessage], index: int) -> AIMessage:
    """Write a deliverable whose body records which model call produced it.

    Stamping the call index into the content is what lets a test tell version 2
    from version 1 without depending on the feedback text being echoed back.

    Args:
        messages: The conversation so far.
        index: The model-call index.

    Returns:
        A ``write_file`` tool call, or a plain completion after the write.
    """
    if isinstance(messages[-1], ToolMessage):
        return AIMessage(content="Saved. Done.")
    path = deliverable_from(messages)
    return write_call(path, f"# Deliverable\n\nDraft {index} for {path}.")


def _build(settings: Settings, versions: InMemoryDeliverableStore, saver: MemorySaver):
    """Build a campaign graph wired with scripted fakes and a shared checkpointer.

    Args:
        settings: The harness settings.
        versions: The deliverable store versions are appended to.
        saver: The checkpointer the run is resumable through.

    Returns:
        The compiled campaign graph.
    """
    return build_campaign_graph(
        settings,
        model=ProgrammableChatModel(handler=_numbered_handler),
        reviewer=FakeReviewer([PASS_VERDICT]),
        checkpointer=saver,
        deliverable_store=versions,
    )


async def test_run_halts_at_the_first_human_stage_and_goes_no_further(
    settings: Settings,
) -> None:
    write_all_agent_specs(settings)
    versions = InMemoryDeliverableStore()
    graph = _build(settings, versions, MemorySaver())

    state = await graph.ainvoke({"tenant": TENANT, "slug": SLUG}, config=_config("halt"))

    assert [record["stage"] for record in state["results"]] == ["research", "brand-strategy"]
    campaign = settings.tenant_dir(TENANT) / "campaigns" / SLUG
    assert not (campaign / "campaign-strategy.md").is_file()


async def test_auto_policy_stage_advances_with_no_human_involvement(
    settings: Settings,
) -> None:
    write_all_agent_specs(settings)
    versions = InMemoryDeliverableStore()
    graph = _build(settings, versions, MemorySaver())

    await graph.ainvoke({"tenant": TENANT, "slug": SLUG}, config=_config("auto"))

    assert versions.latest(TENANT, SLUG, "research") is not None
    assert (settings.tenant_dir(TENANT) / "campaigns" / SLUG / "brand-strategy.md").is_file()


async def test_the_halted_stage_is_reported_from_the_checkpoint(settings: Settings) -> None:
    write_all_agent_specs(settings)
    saver = MemorySaver()
    graph = _build(settings, InMemoryDeliverableStore(), saver)
    config = _config("reported")

    await graph.ainvoke({"tenant": TENANT, "slug": SLUG}, config=config)
    snapshot = await graph.aget_state(config)

    assert [pending.value["stage"] for pending in snapshot.interrupts] == ["brand-strategy"]


async def test_approving_resumes_into_the_next_stage(settings: Settings) -> None:
    write_all_agent_specs(settings)
    saver = MemorySaver()
    graph = _build(settings, InMemoryDeliverableStore(), saver)
    config = _config("approve")
    await graph.ainvoke({"tenant": TENANT, "slug": SLUG}, config=config)

    state = await graph.ainvoke(
        Command(resume={"stage_key": "brand-strategy", "approved": True}), config=config
    )

    assert [record["stage"] for record in state["results"]] == [
        "research",
        "brand-strategy",
        "campaign-strategy",
    ]
    assert (settings.tenant_dir(TENANT) / "campaigns" / SLUG / "campaign-strategy.md").is_file()


async def test_revising_produces_a_new_version_and_keeps_the_prior_one(
    settings: Settings,
) -> None:
    write_all_agent_specs(settings)
    versions = InMemoryDeliverableStore()
    graph = _build(settings, versions, MemorySaver())
    config = _config("revise")
    await graph.ainvoke({"tenant": TENANT, "slug": SLUG}, config=config)
    first = versions.latest(TENANT, SLUG, "brand-strategy")

    await graph.ainvoke(
        Command(
            resume={
                "stage_key": "brand-strategy",
                "approved": False,
                "feedback": "Anchor it to convenience, not premium.",
            }
        ),
        config=config,
    )

    history = versions.history(TENANT, SLUG, "brand-strategy")
    assert [version.version for version in history] == [2, 1]
    assert history[0].feedback == "Anchor it to convenience, not premium."
    assert history[0].feedback_source == "human"
    assert history[0].supersedes_version == 1
    assert versions.version(TENANT, SLUG, "brand-strategy", 1).content == first.content
    assert history[0].content != first.content


async def test_the_specialist_is_told_what_the_owner_asked_for(settings: Settings) -> None:
    write_all_agent_specs(settings)
    seen: list[str] = []

    def recording_handler(messages: list[BaseMessage], index: int) -> AIMessage:
        seen.append("\n".join(str(message.content) for message in messages))
        return _numbered_handler(messages, index)

    graph = build_campaign_graph(
        settings,
        model=ProgrammableChatModel(handler=recording_handler),
        reviewer=FakeReviewer([PASS_VERDICT]),
        checkpointer=MemorySaver(),
        deliverable_store=InMemoryDeliverableStore(),
    )
    config = _config("feedback")
    await graph.ainvoke({"tenant": TENANT, "slug": SLUG}, config=config)
    await graph.ainvoke(
        Command(
            resume={
                "stage_key": "brand-strategy",
                "approved": False,
                "feedback": "Our price point is mid-market.",
            }
        ),
        config=config,
    )

    assert any("Our price point is mid-market." in prompt for prompt in seen)


async def test_a_revised_stage_still_gates_before_the_next_one(settings: Settings) -> None:
    write_all_agent_specs(settings)
    graph = _build(settings, InMemoryDeliverableStore(), MemorySaver())
    config = _config("regate")
    await graph.ainvoke({"tenant": TENANT, "slug": SLUG}, config=config)

    await graph.ainvoke(
        Command(resume={"stage_key": "brand-strategy", "approved": False, "feedback": "again"}),
        config=config,
    )
    snapshot = await graph.aget_state(config)

    assert [pending.value["stage"] for pending in snapshot.interrupts] == ["brand-strategy"]
    assert not (settings.tenant_dir(TENANT) / "campaigns" / SLUG / "campaign-strategy.md").is_file()


async def test_asset_prompts_are_unreachable_while_an_upstream_stage_is_unapproved(
    settings: Settings,
) -> None:
    write_all_agent_specs(settings)
    graph = _build(settings, InMemoryDeliverableStore(), MemorySaver())
    config = _config("blocked")

    await graph.ainvoke({"tenant": TENANT, "slug": SLUG}, config=config)

    campaign = settings.tenant_dir(TENANT) / "campaigns" / SLUG
    assert not (campaign / "creative-brief.md").is_file()
    assert not (campaign / "asset-prompts.md").is_file()


async def test_a_halted_run_survives_a_rebuilt_graph_and_is_still_approvable(
    settings: Settings,
) -> None:
    """A gate that only a live process can answer is not a gate at all.

    Rebuilding the graph over the same checkpointer stands in for the restart:
    nothing of the first graph object survives, and the halted run is still
    there to be approved.
    """
    write_all_agent_specs(settings)
    saver = MemorySaver()
    versions = InMemoryDeliverableStore()
    config = _config(f"{TENANT}/{SLUG}")
    await _build(settings, versions, saver).ainvoke({"tenant": TENANT, "slug": SLUG}, config=config)

    waiting = await awaiting_approval_stage(TENANT, SLUG, checkpointer=saver)
    assert waiting == "brand-strategy"

    state = await _build(settings, versions, saver).ainvoke(
        Command(resume={"stage_key": "brand-strategy", "approved": True}), config=config
    )

    assert [record["stage"] for record in state["results"]][-1] == "campaign-strategy"


async def test_nothing_is_awaiting_approval_on_an_unstarted_campaign(settings: Settings) -> None:
    assert await awaiting_approval_stage(TENANT, SLUG, checkpointer=MemorySaver()) is None


def _make_client(repo: Path) -> TestClient:
    """Build a TestClient bound to the hermetic repo with caches cleared.

    Args:
        repo: The hermetic repository root fixture.

    Returns:
        A configured (not yet entered) FastAPI test client.
    """
    from marketing_os.entrypoints.api.app import app, get_settings

    get_settings.cache_clear()
    install_prototype_adapters(repo)
    authenticate(app)
    return TestClient(app)


def _wait_for_status(client: TestClient, run_id: str, target: str) -> dict:
    """Poll a run's status until it reaches ``target`` or time out.

    Args:
        client: The entered test client.
        run_id: The run id to poll.
        target: The status to wait for.

    Returns:
        The status payload once it matches ``target``.
    """
    for _ in range(300):
        response = client.get(f"/runs/{run_id}")
        if response.status_code == 200 and response.json()["status"] == target:
            return response.json()
        time.sleep(0.02)
    raise AssertionError(f"run {run_id} never reached status {target!r}")


@pytest.fixture
def client(repo: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Yield a hermetic API client with the scripted graph installed.

    Args:
        repo: The hermetic repository root fixture.
        monkeypatch: The pytest monkeypatch fixture.

    Yields:
        An entered FastAPI test client.
    """
    monkeypatch.setenv("MARKETING_OS_ROOT", str(repo))
    write_all_agent_specs(Settings(root=repo))
    install_scripted_graph(monkeypatch, handler=_numbered_handler)
    from marketing_os.entrypoints.api.app import get_settings

    with _make_client(repo) as entered:
        yield entered
    get_settings.cache_clear()
    clear_prototype_adapters()


def test_run_reports_awaiting_approval_rather_than_completed(client: TestClient) -> None:
    run_id = client.post(f"/campaigns/{SLUG}/run", json={}).json()["run_id"]
    status = _wait_for_status(client, run_id, "awaiting_approval")
    assert status["status"] == "awaiting_approval"


def test_stages_endpoint_reports_each_stage_approval_policy(client: TestClient) -> None:
    body = client.get(f"/campaigns/{SLUG}/stages").json()
    policies = {stage["key"]: stage["approval_policy"] for stage in body["stages"]}
    assert policies["research"] == "auto"
    assert policies["brand-strategy"] == "human"
    assert policies["asset-prompts"] == "human"


def test_stages_endpoint_reports_the_operator_phase_each_stage_belongs_to(
    client: TestClient,
) -> None:
    """The stepper groups by Phase, so the engine reports it without adopting UI words."""
    body = client.get(f"/campaigns/{SLUG}/stages").json()
    phases = [(stage["key"], stage["phase"]) for stage in body["stages"]]
    assert phases == [
        ("research", "Research"),
        ("brand-strategy", "Strategy"),
        ("campaign-strategy", "Strategy"),
        ("performance-plan", "Plan"),
        ("creative-brief", "Produce"),
        ("asset-prompts", "Produce"),
    ]


def test_stages_endpoint_marks_the_stage_that_is_waiting_on_a_person(
    client: TestClient,
) -> None:
    run_id = client.post(f"/campaigns/{SLUG}/run", json={}).json()["run_id"]
    _wait_for_status(client, run_id, "awaiting_approval")

    body = client.get(f"/campaigns/{SLUG}/stages").json()

    states = {stage["key"]: stage["state"] for stage in body["stages"]}
    assert states["research"] == "completed"
    assert states["brand-strategy"] == "awaiting_approval"
    assert states["campaign-strategy"] == "pending"


def test_approving_resumes_the_same_run_into_the_next_stage(client: TestClient) -> None:
    run_id = client.post(f"/campaigns/{SLUG}/run", json={}).json()["run_id"]
    _wait_for_status(client, run_id, "awaiting_approval")

    response = client.post(f"/runs/{run_id}/approve", json={"stage_key": "brand-strategy"})

    assert response.status_code == 200
    assert response.json()["run_id"] == run_id
    _wait_for_status(client, run_id, "awaiting_approval")
    versions = client.get(f"/campaigns/{SLUG}/deliverables/campaign-strategy.md/versions")
    assert versions.status_code == 200


def test_revising_produces_a_second_version_carrying_the_feedback(client: TestClient) -> None:
    run_id = client.post(f"/campaigns/{SLUG}/run", json={}).json()["run_id"]
    _wait_for_status(client, run_id, "awaiting_approval")

    response = client.post(
        f"/runs/{run_id}/revise",
        json={"stage_key": "brand-strategy", "feedback": "Too premium; we are mid-market."},
    )
    assert response.status_code == 202
    _wait_for_status(client, run_id, "awaiting_approval")

    body = client.get(f"/campaigns/{SLUG}/deliverables/brand-strategy.md/versions").json()
    assert [version["version"] for version in body["versions"]] == [2, 1]
    assert body["versions"][0]["feedback"] == "Too premium; we are mid-market."
    assert body["versions"][0]["feedback_source"] == "human"
    assert body["versions"][1]["feedback"] is None


def test_a_prior_version_is_still_readable_after_a_revision(client: TestClient) -> None:
    run_id = client.post(f"/campaigns/{SLUG}/run", json={}).json()["run_id"]
    _wait_for_status(client, run_id, "awaiting_approval")
    first = client.get(f"/campaigns/{SLUG}/deliverables/brand-strategy.md/versions/1").json()

    client.post(
        f"/runs/{run_id}/revise", json={"stage_key": "brand-strategy", "feedback": "sharper"}
    )
    _wait_for_status(client, run_id, "awaiting_approval")

    still = client.get(f"/campaigns/{SLUG}/deliverables/brand-strategy.md/versions/1").json()
    assert still["content"] == first["content"]
    assert still["latest"] is False


def test_approving_a_stage_that_is_not_waiting_is_refused(client: TestClient) -> None:
    run_id = client.post(f"/campaigns/{SLUG}/run", json={}).json()["run_id"]
    _wait_for_status(client, run_id, "awaiting_approval")

    response = client.post(f"/runs/{run_id}/approve", json={"stage_key": "creative-brief"})

    assert response.status_code == 409
    assert response.json()["type"] == "stage_not_awaiting_approval"


def test_revising_with_empty_feedback_is_refused(client: TestClient) -> None:
    run_id = client.post(f"/campaigns/{SLUG}/run", json={}).json()["run_id"]
    _wait_for_status(client, run_id, "awaiting_approval")

    response = client.post(
        f"/runs/{run_id}/revise", json={"stage_key": "brand-strategy", "feedback": "   "}
    )

    assert response.status_code == 422


def test_revisions_are_capped_per_deliverable(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from marketing_os.entrypoints.api.app import get_settings

    monkeypatch.setattr(get_settings(), "max_revisions", 1)
    run_id = client.post(f"/campaigns/{SLUG}/run", json={}).json()["run_id"]
    _wait_for_status(client, run_id, "awaiting_approval")
    client.post(f"/runs/{run_id}/revise", json={"stage_key": "brand-strategy", "feedback": "one"})
    _wait_for_status(client, run_id, "awaiting_approval")

    response = client.post(
        f"/runs/{run_id}/revise", json={"stage_key": "brand-strategy", "feedback": "two"}
    )

    assert response.status_code == 409
    assert response.json()["type"] == "revision_limit_reached"


def test_a_halted_run_still_holds_its_campaign(client: TestClient) -> None:
    run_id = client.post(f"/campaigns/{SLUG}/run", json={}).json()["run_id"]
    _wait_for_status(client, run_id, "awaiting_approval")

    second = client.post(f"/campaigns/{SLUG}/run", json={})

    assert second.status_code == 409
    assert second.json()["type"] == "run_conflict"
    assert second.json()["active_run_id"] == run_id


def test_approve_404_for_an_unknown_run(client: TestClient) -> None:
    response = client.post("/runs/run_missing/approve", json={"stage_key": "brand-strategy"})
    assert response.status_code == 404


def test_a_halted_run_can_be_cancelled(client: TestClient) -> None:
    run_id = client.post(f"/campaigns/{SLUG}/run", json={}).json()["run_id"]
    _wait_for_status(client, run_id, "awaiting_approval")

    response = client.post(f"/runs/{run_id}/cancel")

    assert response.status_code == 200
    assert client.get(f"/runs/{run_id}").json()["status"] == "cancelled"


async def test_a_qa_driven_revision_is_recorded_as_the_reviewers_feedback(
    settings: Settings,
) -> None:
    """Both the gate and the reviewer can send a stage back; the version says which."""
    from conftest import FAIL_VERDICT

    write_all_agent_specs(settings)
    versions = InMemoryDeliverableStore()
    graph = build_campaign_graph(
        settings,
        model=ProgrammableChatModel(handler=_numbered_handler),
        reviewer=FakeReviewer([FAIL_VERDICT, PASS_VERDICT]),
        checkpointer=MemorySaver(),
        deliverable_store=versions,
    )

    await graph.ainvoke({"tenant": TENANT, "slug": SLUG}, config=_config("qa-feedback"))

    research = versions.latest(TENANT, SLUG, "research")
    assert research.version == 1
    assert research.feedback_source == "reviewer"
    assert research.feedback == FAIL_VERDICT.summary


async def test_the_graph_refuses_a_revision_past_the_cap(settings: Settings) -> None:
    """The cap binds every driver of the graph, not only the HTTP endpoint."""
    settings.max_revisions = 1
    write_all_agent_specs(settings)
    versions = InMemoryDeliverableStore()
    graph = _build(settings, versions, MemorySaver())
    config = _config("capped")
    await graph.ainvoke({"tenant": TENANT, "slug": SLUG}, config=config)
    send_back = Command(
        resume={"stage_key": "brand-strategy", "approved": False, "feedback": "again"}
    )

    await graph.ainvoke(send_back, config=config)
    state = await graph.ainvoke(send_back, config=config)

    assert state["error"]["type"] == "revision_limit"
    assert state["error"]["limit"] == 1
    assert [version.version for version in versions.history(TENANT, SLUG, "brand-strategy")] == [
        2,
        1,
    ]


def test_the_gate_reports_revisions_used_from_the_version_chain(client: TestClient) -> None:
    """The number shown at the gate is the number the cap enforces.

    LangGraph re-executes the interrupted node when the run resumes, so the gate
    announces itself again before consuming the decision — hence a repeat of the
    count that was already showing. What matters is that the last announcement
    reflects the revision that has now been spent.
    """
    run_id = client.post(f"/campaigns/{SLUG}/run", json={}).json()["run_id"]
    _wait_for_status(client, run_id, "awaiting_approval")
    client.post(f"/runs/{run_id}/revise", json={"stage_key": "brand-strategy", "feedback": "one"})
    _wait_for_status(client, run_id, "awaiting_approval")

    events = client.get(f"/campaigns/{SLUG}/runs/{run_id}").json()["events"]
    waiting = [event for event in events if event["event"] == "stage.awaiting_approval"]

    assert [event["revisions_used"] for event in waiting][-1] == 1
    assert all(event["revisions_allowed"] == 5 for event in waiting)


def test_a_gate_the_store_lost_track_of_is_still_approvable(client: TestClient) -> None:
    """The checkpoint decides whether a person is being waited on, not the store.

    Forcing the record back to ``running`` stands in for a startup sweep that
    raced a halt. The gate is plainly there in the checkpoint, so the owner's
    approval must land rather than being told nothing is waiting.
    """
    from marketing_os.adapters.runs import RUNNING
    from marketing_os.entrypoints.api.app import get_run_store

    run_id = client.post(f"/campaigns/{SLUG}/run", json={}).json()["run_id"]
    _wait_for_status(client, run_id, "awaiting_approval")
    get_run_store().set_live_status(run_id, RUNNING)

    response = client.post(f"/runs/{run_id}/approve", json={"stage_key": "brand-strategy"})

    assert response.status_code == 200
    _wait_for_status(client, run_id, "awaiting_approval")
    assert client.get(f"/campaigns/{SLUG}/deliverables/campaign-strategy.md").status_code == 200

"""Clarifications: the specialist asks the business for a fact, and the run halts.

A specialist that lacks a fact only the business knows must ask for it rather
than infer it (ADR-0028). What is pinned here is what a business owner or an
operator can observe: the run and the campaign read ``awaiting_clarification``,
the questions and their reasons are readable from the run, nothing is written
on a guess, the partial work is billed, and a stage that keeps asking past its
cap halts with a clear error rather than proceeding.

The graph-level tests drive the compiled graph through the runner so the halt
is observable without HTTP; the API tests prove the same through the endpoints
the interface calls. Both use scripted models and fake reviewers.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from conftest import (
    ASK_QUESTIONS,
    PASS_VERDICT,
    SLUG,
    TENANT,
    FakeReviewer,
    Handler,
    ProgrammableChatModel,
    asking_handler,
    authenticate,
    clear_prototype_adapters,
    install_prototype_adapters,
    install_scripted_graph,
    prototype_adapters,
    write_all_agent_specs,
    writing_handler,
)
from marketing_os.adapters.observability import read_events
from marketing_os.adapters.usage import InMemoryUsageLedger
from marketing_os.config import Settings
from marketing_os.errors import ClarificationLimitError
from marketing_os.graph.graph import build_campaign_graph
from marketing_os.graph.runner import arun_campaign, awaiting_approval_stage, pending_hold
from marketing_os.questionnaire import SEED_QUESTIONNAIRE


def _adapters(settings: Settings, saver: MemorySaver) -> dict[str, Any]:
    """Build the runner's storage arguments against the hermetic repo.

    Args:
        settings: The harness settings.
        saver: The checkpointer the run is resumable through.

    Returns:
        The keyword arguments :func:`arun_campaign` requires.
    """
    return {**prototype_adapters(settings.root), "checkpointer": saver}


async def test_the_run_halts_and_reports_the_questions_it_is_holding_for(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_all_agent_specs(settings)
    install_scripted_graph(monkeypatch, handler=asking_handler("research"))
    saver = MemorySaver()

    result = await arun_campaign(settings, TENANT, SLUG, **_adapters(settings, saver))

    assert result.awaiting_clarification_stage == "research"
    assert result.awaiting_approval_stage is None
    hold = await pending_hold(TENANT, SLUG, checkpointer=saver)
    assert hold is not None
    assert hold.kind == "clarification"
    assert hold.stage == "research"
    assert [question.model_dump() for question in hold.questions] == ASK_QUESTIONS


async def test_a_clarification_hold_is_not_an_approval_gate(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Approving a run that is asking a question must be refused, so the two never blur."""
    write_all_agent_specs(settings)
    install_scripted_graph(monkeypatch, handler=asking_handler("research"))
    saver = MemorySaver()

    await arun_campaign(settings, TENANT, SLUG, **_adapters(settings, saver))

    assert await awaiting_approval_stage(TENANT, SLUG, checkpointer=saver) is None


async def test_nothing_is_written_on_a_guess(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_all_agent_specs(settings)
    install_scripted_graph(monkeypatch, handler=asking_handler("research"))

    result = await arun_campaign(settings, TENANT, SLUG, **_adapters(settings, MemorySaver()))

    assert result.stages == []
    assert not (settings.tenant_dir(TENANT) / "campaigns" / SLUG / "research.md").is_file()


async def test_a_later_stage_can_ask_after_earlier_ones_completed(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_all_agent_specs(settings)
    install_scripted_graph(monkeypatch, handler=asking_handler("brand-strategy"))
    saver = MemorySaver()

    result = await arun_campaign(settings, TENANT, SLUG, **_adapters(settings, saver))

    assert [stage.stage for stage in result.stages] == ["research"]
    assert result.awaiting_clarification_stage == "brand-strategy"


async def test_asking_past_the_cap_halts_with_a_clarification_error(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The run never proceeds on a guess; a confused specialist is stopped instead."""
    write_all_agent_specs(settings)
    settings.max_clarifications = 1
    install_scripted_graph(monkeypatch, handler=asking_handler("research"))
    adapters = _adapters(settings, MemorySaver())
    await arun_campaign(settings, TENANT, SLUG, **adapters)

    with pytest.raises(ClarificationLimitError) as raised:
        await arun_campaign(
            settings, TENANT, SLUG, **adapters, resume=Command(resume={"answered": True})
        )

    assert raised.value.detail is not None
    assert raised.value.detail["halt_reason"] == "clarification"
    assert raised.value.detail["stage"] == "research"
    assert raised.value.detail["limit"] == 1
    assert raised.value.detail["questions"] == ASK_QUESTIONS
    assert ASK_QUESTIONS[0]["question"] in str(raised.value)


async def test_the_cap_is_read_from_settings(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With room left under the cap, a second ask halts again rather than erroring."""
    write_all_agent_specs(settings)
    settings.max_clarifications = 2
    install_scripted_graph(monkeypatch, handler=asking_handler("research"))
    adapters = _adapters(settings, MemorySaver())
    await arun_campaign(settings, TENANT, SLUG, **adapters)

    result = await arun_campaign(
        settings, TENANT, SLUG, **adapters, resume=Command(resume={"answered": True})
    )

    assert result.awaiting_clarification_stage == "research"


def test_the_default_cap_is_two(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("MARKETING_OS_MAX_CLARIFICATIONS", raising=False)
    assert Settings(root=tmp_path).max_clarifications == 2

    monkeypatch.setenv("MARKETING_OS_MAX_CLARIFICATIONS", "5")
    assert Settings(root=tmp_path).max_clarifications == 5


async def test_the_ledger_is_charged_for_the_work_before_the_halt(settings: Settings) -> None:
    write_all_agent_specs(settings)
    ledger = InMemoryUsageLedger(settings)
    adapters = _adapters(settings, MemorySaver())
    graph = build_campaign_graph(
        settings,
        model=ProgrammableChatModel(handler=asking_handler("research")),
        reviewer=FakeReviewer([PASS_VERDICT]),
        checkpointer=MemorySaver(),
        document_store=adapters["document_store"],
        deliverable_store=adapters["deliverable_store"],
        usage_ledger=ledger,
        questionnaire=SEED_QUESTIONNAIRE,
    )

    await graph.ainvoke(
        {"tenant": TENANT, "slug": SLUG}, config={"configurable": {"thread_id": "billed"}}
    )

    entries = ledger.entries(TENANT, SLUG)
    assert [entry.stage_key for entry in entries] == ["research"]
    assert entries[0].units > 0


async def test_the_trace_carries_the_questions(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_all_agent_specs(settings)
    install_scripted_graph(monkeypatch, handler=asking_handler("research"))

    result = await arun_campaign(settings, TENANT, SLUG, **_adapters(settings, MemorySaver()))

    assert result.run_log is not None
    events = read_events(settings.root / result.run_log)
    asked = [event for event in events if event["event"] == "stage.awaiting_clarification"]
    assert len(asked) == 1
    assert asked[0]["stage"] == "research"
    assert asked[0]["questions"] == ASK_QUESTIONS
    summary = events[-1]
    assert summary["event"] == "run.summary"
    assert summary["outcome"] == "awaiting_clarification"
    assert summary["stage"] == "research"


@contextmanager
def _client_for(
    repo: Path, monkeypatch: pytest.MonkeyPatch, handler: Handler
) -> Iterator[TestClient]:
    """Enter a hermetic API client whose specialists follow one scripted handler.

    Args:
        repo: The hermetic repository root fixture.
        monkeypatch: The pytest monkeypatch fixture.
        handler: The scripted chat-model handler every specialist follows.

    Yields:
        An entered FastAPI test client, with caches cleared on exit.
    """
    from marketing_os.entrypoints.api.app import app, get_settings

    monkeypatch.setenv("MARKETING_OS_ROOT", str(repo))
    write_all_agent_specs(Settings(root=repo))
    install_scripted_graph(monkeypatch, handler=handler)
    get_settings.cache_clear()
    install_prototype_adapters(repo)
    authenticate(app)
    with TestClient(app) as entered:
        yield entered
    get_settings.cache_clear()
    clear_prototype_adapters()


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
    """Yield a hermetic API client whose brand-strategy specialist asks a question.

    Args:
        repo: The hermetic repository root fixture.
        monkeypatch: The pytest monkeypatch fixture.

    Yields:
        An entered FastAPI test client.
    """
    with _client_for(repo, monkeypatch, asking_handler("brand-strategy")) as entered:
        yield entered


def _halt(client: TestClient) -> str:
    """Start the campaign's run and wait for it to halt on a question.

    Args:
        client: The entered test client.

    Returns:
        The halted run's id.
    """
    run_id = client.post(f"/campaigns/{SLUG}/run", json={}).json()["run_id"]
    _wait_for_status(client, run_id, "awaiting_clarification")
    return run_id


def test_the_run_reports_awaiting_clarification(client: TestClient) -> None:
    run_id = _halt(client)

    assert client.get(f"/runs/{run_id}").json()["status"] == "awaiting_clarification"


def test_the_campaign_and_its_stage_read_awaiting_clarification(client: TestClient) -> None:
    _halt(client)

    campaign = client.get(f"/campaigns/{SLUG}").json()
    assert campaign["status"] == "awaiting_clarification"
    states = {stage["key"]: stage["state"] for stage in campaign["stages"]}
    assert states["research"] == "completed"
    assert states["brand-strategy"] == "awaiting_clarification"

    listed = client.get("/campaigns").json()["campaigns"]
    summary = next(item for item in listed if item["id"] == SLUG)
    assert summary["status"] == "awaiting_clarification"
    assert summary["blocked_reason"] == "Strategy has a question for you."


def test_the_questions_and_reasons_are_readable_from_the_run(client: TestClient) -> None:
    run_id = _halt(client)

    response = client.get(f"/runs/{run_id}/clarifications")

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == run_id
    assert body["slug"] == SLUG
    assert body["stage"] == "brand-strategy"
    assert body["questions"] == ASK_QUESTIONS


def test_a_halted_run_still_holds_its_campaign(client: TestClient) -> None:
    _halt(client)

    response = client.post(f"/campaigns/{SLUG}/run", json={})

    assert response.status_code == 409


def test_approving_a_run_that_is_asking_is_refused(client: TestClient) -> None:
    run_id = _halt(client)

    response = client.post(f"/runs/{run_id}/approve", json={"stage_key": "brand-strategy"})

    assert response.status_code == 409


def test_a_run_holding_for_a_question_can_be_cancelled(client: TestClient) -> None:
    run_id = _halt(client)

    response = client.post(f"/runs/{run_id}/cancel")

    assert response.status_code == 200
    assert client.get(f"/runs/{run_id}").json()["status"] == "cancelled"


def test_clarifications_404_for_an_unknown_run(client: TestClient) -> None:
    assert client.get("/runs/ghost/clarifications").status_code == 404


def test_clarifications_409_for_a_run_not_asking(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with _client_for(repo, monkeypatch, writing_handler) as client:
        run_id = client.post(f"/campaigns/{SLUG}/run", json={}).json()["run_id"]
        _wait_for_status(client, run_id, "awaiting_approval")

        response = client.get(f"/runs/{run_id}/clarifications")

    assert response.status_code == 409
    assert response.json()["type"] == "run_not_awaiting_clarification"

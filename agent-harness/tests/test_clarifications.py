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
    OTHER_TENANT,
    PASS_VERDICT,
    SLUG,
    TENANT,
    FakeReviewer,
    Handler,
    ProgrammableChatModel,
    answered_clarifications,
    asking_handler,
    asking_until_answered_handler,
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
from marketing_os.questionnaire import CLARIFICATIONS_HEADING, SEED_QUESTIONNAIRE, render_brand_dna
from marketing_os.schemas import BrandDnaRecord, DnaAnswer


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


def _answer_in_the_dna(settings: Settings, stage: str) -> str:
    """Write the business's answers to :data:`ASK_QUESTIONS` into its Brand DNA.

    What the answer endpoint does once it has saved the Clarifications: the DNA
    the specialists read is re-rendered so the re-run is seeded from it.

    Args:
        settings: The harness settings locating the tenant's documents.
        stage: The stage that asked.

    Returns:
        The rendered DNA now on disk.
    """
    record = BrandDnaRecord(
        questionnaire_version=SEED_QUESTIONNAIRE.version,
        answers=[
            DnaAnswer(question_id=question.id, answer=f"Answer to {question.field}")
            for question in SEED_QUESTIONNAIRE.required_questions
        ],
        clarifications=answered_clarifications(stage),
    )
    rendered = render_brand_dna(SEED_QUESTIONNAIRE, record, business_name="Acme")
    (settings.tenant_dir(TENANT) / "dna.md").write_text(rendered, encoding="utf-8")
    return rendered


async def test_answering_re_runs_the_stage_from_the_updated_dna(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The stage re-enters seeded with a DNA that carries the answers, and continues."""
    write_all_agent_specs(settings)
    model = ProgrammableChatModel(handler=asking_until_answered_handler("research"))
    install_scripted_graph(monkeypatch, model_factory=lambda: model)
    adapters = _adapters(settings, MemorySaver())
    halted = await arun_campaign(settings, TENANT, SLUG, **adapters)
    assert halted.awaiting_clarification_stage == "research"
    _answer_in_the_dna(settings, "research")

    resumed = await arun_campaign(
        settings, TENANT, SLUG, **adapters, resume=Command(resume={"answered": True})
    )

    assert resumed.awaiting_clarification_stage is None
    assert resumed.awaiting_approval_stage == "brand-strategy"
    assert [stage.stage for stage in resumed.stages] == ["research", "brand-strategy"]
    seeded = next(
        text
        for text in model.received
        if "campaigns/" + SLUG + "/research.md" in text and CLARIFICATIONS_HEADING in text
    )
    assert CLARIFICATIONS_HEADING in seeded
    for clarification in answered_clarifications("research"):
        assert clarification.answer in seeded


async def test_the_trace_carries_the_answer(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_all_agent_specs(settings)
    install_scripted_graph(monkeypatch, handler=asking_until_answered_handler("research"))
    adapters = _adapters(settings, MemorySaver())
    halted = await arun_campaign(settings, TENANT, SLUG, **adapters)
    _answer_in_the_dna(settings, "research")

    resumed = await arun_campaign(
        settings, TENANT, SLUG, **adapters, resume=Command(resume={"answered": True})
    )

    assert halted.run_log is not None
    events = read_events(settings.root / halted.run_log) + read_events(
        settings.root / str(resumed.run_log)
    )
    names = [event["event"] for event in events]
    asked = names.index("stage.awaiting_clarification")
    clarified = names.index("stage.clarified")
    assert asked < clarified < names.index("stage.start", clarified)
    assert events[clarified]["stage"] == "research"
    assert events[clarified]["questions"] == ASK_QUESTIONS


async def test_a_later_campaign_is_seeded_with_the_answer_and_never_asks_again(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_all_agent_specs(settings)
    model = ProgrammableChatModel(handler=asking_until_answered_handler("research"))
    install_scripted_graph(monkeypatch, model_factory=lambda: model)
    _answer_in_the_dna(settings, "research")
    second = "second-push"
    goal = settings.tenant_dir(TENANT) / "campaigns" / SLUG / "goal.md"
    target = settings.tenant_dir(TENANT) / "campaigns" / second / "goal.md"
    target.parent.mkdir(parents=True)
    target.write_text(goal.read_text(encoding="utf-8"), encoding="utf-8")

    result = await arun_campaign(settings, TENANT, second, **_adapters(settings, MemorySaver()))

    assert result.awaiting_clarification_stage is None
    assert result.awaiting_approval_stage == "brand-strategy"
    assert CLARIFICATIONS_HEADING in model.received[0]


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


def _answers() -> list[dict[str, str]]:
    """Answer both of :data:`ASK_QUESTIONS`, as the owner would from the screen.

    Returns:
        The request body's ``answers``.
    """
    return [
        {"question": ASK_QUESTIONS[0]["question"], "answer": "Yes, about 1,200 subscribers."},
        {"question": ASK_QUESTIONS[1]["question"], "answer": "About 1,200."},
    ]


@pytest.fixture
def answering_client(repo: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Yield a client whose brand-strategy specialist asks until its DNA carries the answer.

    Args:
        repo: The hermetic repository root fixture.
        monkeypatch: The pytest monkeypatch fixture.

    Yields:
        An entered FastAPI test client.
    """
    with _client_for(repo, monkeypatch, asking_until_answered_handler("brand-strategy")) as entered:
        yield entered


def test_answering_saves_the_clarifications_and_the_run_continues_to_its_next_gate(
    answering_client: TestClient,
) -> None:
    client = answering_client
    run_id = _halt(client)

    response = client.post(f"/runs/{run_id}/clarifications", json={"answers": _answers()})

    assert response.status_code == 202, response.text
    assert response.json() == {
        "run_id": run_id,
        "slug": SLUG,
        "stage": "brand-strategy",
        "status": "running",
    }
    _wait_for_status(client, run_id, "awaiting_approval")
    campaign = client.get(f"/campaigns/{SLUG}").json()
    assert campaign["status"] == "awaiting_approval"
    states = {stage["key"]: stage["state"] for stage in campaign["stages"]}
    assert states["brand-strategy"] == "awaiting_approval"

    dna = client.get("/brand-dna").json()
    assert [item["question"] for item in dna["clarifications"]] == [
        question["question"] for question in ASK_QUESTIONS
    ]
    saved = dna["clarifications"][0]
    assert saved["answer"] == "Yes, about 1,200 subscribers."
    assert saved["reason"] == ASK_QUESTIONS[0]["reason"]
    assert saved["stage"] == "brand-strategy"
    assert saved["slug"] == SLUG
    assert saved["id"].startswith("clr_")
    assert CLARIFICATIONS_HEADING in dna["markdown"]
    assert "Yes, about 1,200 subscribers." in dna["markdown"]


def test_the_completeness_report_ignores_the_clarifications(
    answering_client: TestClient,
) -> None:
    client = answering_client
    before = client.get("/brand-dna/completeness").json()
    run_id = _halt(client)

    client.post(f"/runs/{run_id}/clarifications", json={"answers": _answers()})

    assert client.get("/brand-dna/completeness").json() == before


def test_the_stage_re_runs_from_the_dna_the_answers_were_saved_into(
    answering_client: TestClient,
) -> None:
    """The trace shows the answer landing, then the stage starting over from it."""
    client = answering_client
    run_id = _halt(client)

    client.post(f"/runs/{run_id}/clarifications", json={"answers": _answers()})
    _wait_for_status(client, run_id, "awaiting_approval")

    events = client.get(f"/campaigns/{SLUG}/runs/{run_id}").json()["events"]
    names = [event["event"] for event in events]
    assert "stage.clarified" in names
    assert names.index("stage.clarified") < len(names) - 1 - names[::-1].index("stage.start")


def test_answering_a_run_that_is_not_asking_is_refused(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with _client_for(repo, monkeypatch, writing_handler) as client:
        run_id = client.post(f"/campaigns/{SLUG}/run", json={}).json()["run_id"]
        _wait_for_status(client, run_id, "awaiting_approval")

        response = client.post(f"/runs/{run_id}/clarifications", json={"answers": _answers()})
        status = client.get(f"/runs/{run_id}").json()["status"]

    assert response.status_code == 409
    assert response.json()["type"] == "run_not_awaiting_clarification"
    assert status == "awaiting_approval"


def test_a_colleague_cannot_answer_and_nothing_is_saved(answering_client: TestClient) -> None:
    """A run is driven by the person who started it; to a colleague it reads as absent."""
    from marketing_os.entrypoints.api.app import app

    client = answering_client
    run_id = _halt(client)
    authenticate(app, user="usr_colleague")

    response = client.post(f"/runs/{run_id}/clarifications", json={"answers": _answers()})

    authenticate(app)
    assert response.status_code == 404
    assert client.get("/brand-dna").json()["clarifications"] == []
    assert client.get(f"/runs/{run_id}").json()["status"] == "awaiting_clarification"


def test_answering_an_unknown_run_is_404(answering_client: TestClient) -> None:
    response = answering_client.post("/runs/ghost/clarifications", json={"answers": _answers()})

    assert response.status_code == 404


def test_leaving_a_question_unanswered_is_refused(answering_client: TestClient) -> None:
    client = answering_client
    run_id = _halt(client)

    response = client.post(f"/runs/{run_id}/clarifications", json={"answers": _answers()[:1]})

    assert response.status_code == 422
    assert ASK_QUESTIONS[1]["question"] in response.json()["message"]
    assert client.get(f"/runs/{run_id}").json()["status"] == "awaiting_clarification"
    assert client.get("/brand-dna").json()["clarifications"] == []


def test_a_blank_answer_is_refused(answering_client: TestClient) -> None:
    client = answering_client
    run_id = _halt(client)
    answers = _answers()
    answers[0]["answer"] = "   "

    response = client.post(f"/runs/{run_id}/clarifications", json={"answers": answers})

    assert response.status_code == 422
    assert client.get(f"/runs/{run_id}").json()["status"] == "awaiting_clarification"


def test_an_answer_to_a_question_the_run_did_not_ask_is_refused(
    answering_client: TestClient,
) -> None:
    client = answering_client
    run_id = _halt(client)
    answers = [*_answers(), {"question": "What colour is the logo?", "answer": "Blue"}]

    response = client.post(f"/runs/{run_id}/clarifications", json={"answers": answers})

    assert response.status_code == 422
    assert "What colour is the logo?" in response.json()["message"]
    assert client.get("/brand-dna").json()["clarifications"] == []


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


# --- Editing a Clarification: the Brand page's tab ----------------------------

EDITED_ANSWER = "No list yet; we collect emails at the front desk."


def _everything_but_the_dna(client: TestClient, run_id: str) -> dict[str, Any]:
    """Read every campaign-side fact an edit must leave alone.

    Args:
        client: The entered test client.
        run_id: The campaign's run.

    Returns:
        The campaign, its stages, its deliverables and each one's version
        history, the run, the in-flight run list, and the completeness report —
        as the API reports them, so a before/after comparison is byte-for-byte.
    """
    listing = client.get(f"/campaigns/{SLUG}/deliverables").json()
    versions = {}
    for document in listing["files"]:
        response = client.get(f"/campaigns/{SLUG}/deliverables/{document['name']}/versions")
        versions[document["name"]] = (response.status_code, response.json())
    return {
        "campaign": client.get(f"/campaigns/{SLUG}").json(),
        "stages": client.get(f"/campaigns/{SLUG}/stages").json(),
        "deliverables": listing,
        "versions": versions,
        "run": client.get(f"/runs/{run_id}").json(),
        "runs": client.get("/runs").json(),
        "completeness": client.get("/brand-dna/completeness").json(),
    }


def test_editing_a_clarification_changes_the_dna_and_nothing_else(
    answering_client: TestClient, repo: Path
) -> None:
    """An edit is retrospective: it rewrites the Brand DNA and touches no campaign."""
    client = answering_client
    run_id = _halt(client)
    client.post(f"/runs/{run_id}/clarifications", json={"answers": _answers()})
    _wait_for_status(client, run_id, "awaiting_approval")
    saved, other = client.get("/brand-dna").json()["clarifications"]
    before = _everything_but_the_dna(client, run_id)

    response = client.put(
        f"/brand-dna/clarifications/{saved['id']}", json={"answer": EDITED_ANSWER}
    )

    assert response.status_code == 200, response.text
    assert response.json()["id"] == saved["id"]
    assert response.json()["answer"] == EDITED_ANSWER
    dna = client.get("/brand-dna").json()
    edited, kept = dna["clarifications"]
    assert edited["answer"] == EDITED_ANSWER
    unchanged = {key for key in saved if key not in ("answer", "answered_at")}
    assert {key: edited[key] for key in unchanged} == {key: saved[key] for key in unchanged}
    assert kept == other
    assert EDITED_ANSWER in dna["markdown"]
    assert "Yes, about 1,200 subscribers." not in dna["markdown"]
    assert EDITED_ANSWER in (repo / "tenants" / TENANT / "dna.md").read_text()
    assert _everything_but_the_dna(client, run_id) == before


def _seed_clarifications(stage: str = "brand-strategy") -> list[str]:
    """Record answered Clarifications for the tenant, as a past campaign would have.

    Args:
        stage: The stage that asked.

    Returns:
        The ids of the recorded Clarifications, in order.
    """
    from marketing_os.entrypoints.api.app import get_answer_store

    record = get_answer_store().add_clarifications(
        TENANT, clarifications=answered_clarifications(stage)
    )
    return [item.id for item in record.clarifications]


def test_editing_a_clarification_the_business_does_not_have_is_404(client: TestClient) -> None:
    _seed_clarifications()

    response = client.put("/brand-dna/clarifications/clr_missing", json={"answer": EDITED_ANSWER})

    assert response.status_code == 404


def test_a_blank_edit_is_refused_and_the_answer_stands(client: TestClient) -> None:
    first = _seed_clarifications()[0]

    response = client.put(f"/brand-dna/clarifications/{first}", json={"answer": "   "})

    assert response.status_code == 422
    saved = client.get("/brand-dna").json()["clarifications"][0]
    assert saved["answer"] == "Yes, about 1,200 subscribers."


def test_one_business_cannot_edit_anothers_clarification(client: TestClient) -> None:
    """A foreign id is indistinguishable from a missing one (ADR-0013)."""
    from marketing_os.entrypoints.api.app import app

    first = _seed_clarifications()[0]
    authenticate(app, tenant=OTHER_TENANT)

    response = client.put(f"/brand-dna/clarifications/{first}", json={"answer": EDITED_ANSWER})

    authenticate(app)
    assert response.status_code == 404
    saved = client.get("/brand-dna").json()["clarifications"][0]
    assert saved["answer"] == "Yes, about 1,200 subscribers."

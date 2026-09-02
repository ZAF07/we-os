"""The questionnaire → Brand DNA → gate path, driven over HTTP.

The API is the default seam for this behaviour: these assert what an API client
can observe — which questions come back, what a save reports as still missing,
that the rendered DNA is what the gate then reads, and that a business's answers
are invisible to another tenant.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from conftest import OTHER_TENANT, SLUG, TENANT, authenticate, identity_for
from marketing_os.questionnaire import SEED_QUESTIONNAIRE


@pytest.fixture
def client(repo: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Yield a hermetic API client with no Brand DNA authored for the tenant.

    The repo fixture ships a hand-authored ``dna.md``; onboarding is what this
    module is about, so it starts from a business that has answered nothing.

    Args:
        repo: The hermetic repository root fixture.
        monkeypatch: The pytest monkeypatch fixture.

    Yields:
        An entered FastAPI test client.
    """
    monkeypatch.setenv("MARKETING_OS_ROOT", str(repo))
    (repo / "tenants" / TENANT / "dna.md").unlink()
    from marketing_os.entrypoints.api.app import app, get_settings, reset_providers

    get_settings.cache_clear()
    reset_providers()
    authenticate(app)
    with TestClient(app) as entered:
        yield entered
    app.dependency_overrides.clear()
    get_settings.cache_clear()
    reset_providers()


def answer_everything(client: TestClient, *, skip: set[str] | None = None) -> dict:
    """Answer every Required question except the skipped ones.

    Args:
        client: The entered test client.
        skip: Question ids to leave unanswered.

    Returns:
        The completeness report the save returned.
    """
    omit = skip or set()
    response = client.post(
        "/brand-dna/answers",
        json={
            "answers": [
                {"question_id": question.id, "answer": f"Answer to {question.field}"}
                for question in SEED_QUESTIONNAIRE.required_questions
                if question.id not in omit
            ]
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_questionnaire_serves_the_published_question_set(client):
    body = client.get("/questionnaire").json()
    assert body["version"] == SEED_QUESTIONNAIRE.version
    assert len(body["questions"]) == len(SEED_QUESTIONNAIRE.questions)


def test_every_question_carries_why_we_ask_and_help_text(client):
    for question in client.get("/questionnaire").json()["questions"]:
        assert question["why_we_ask"]
        assert question["help_text"]
        assert question["field"]


def test_an_unauthenticated_caller_gets_no_questionnaire(client):
    from marketing_os.entrypoints.api.app import app, get_identity

    app.dependency_overrides.pop(get_identity)
    assert client.get("/questionnaire").status_code == 401
    assert client.get("/brand-dna").status_code == 401
    assert client.post("/brand-dna/answers", json={"answers": []}).status_code == 401


def test_a_business_that_has_answered_nothing_is_incomplete(client):
    report = client.get("/brand-dna/completeness").json()
    assert report["complete"] is False
    assert report["required_answered"] == 0
    assert report["required_total"] == len(SEED_QUESTIONNAIRE.required_questions)


def test_a_business_that_has_answered_nothing_reports_no_answered_version(client):
    # Reporting the published version here would claim the business had already
    # been shown every question, which is exactly what "your DNA predates a
    # newer version" keys off — so an unstarted onboarding reports version 0.
    assert client.get("/brand-dna").json()["questionnaire_version"] == 0
    assert client.get("/brand-dna").json()["updated_at"] is None


def test_saving_partway_reports_exactly_what_remains(client):
    price = next(q for q in SEED_QUESTIONNAIRE.questions if q.field == "Price point")
    report = answer_everything(client, skip={price.id})
    assert report["complete"] is False
    assert [missing["field"] for missing in report["missing"]] == ["Price point"]
    assert report["missing"][0]["label"] == price.text


def test_onboarding_resumes_from_what_was_already_saved(client):
    name = next(q for q in SEED_QUESTIONNAIRE.questions if q.field == "Business name")
    client.post(
        "/brand-dna/answers",
        json={"answers": [{"question_id": name.id, "answer": "Acme Climbing Gym"}]},
    )
    body = client.get("/brand-dna").json()
    assert {"question_id": name.id, "answer": "Acme Climbing Gym"} in body["answers"]
    assert client.get("/brand-dna/completeness").json()["required_answered"] == 1


def test_any_answer_can_be_edited_later(client):
    price = next(q for q in SEED_QUESTIONNAIRE.questions if q.field == "Price point")
    answer_everything(client)
    client.post(
        "/brand-dna/answers",
        json={"answers": [{"question_id": price.id, "answer": "$90 a month"}]},
    )
    body = client.get("/brand-dna").json()
    assert {"question_id": price.id, "answer": "$90 a month"} in body["answers"]
    assert "**Price point:** $90 a month" in body["markdown"]
    assert body["updated_at"]


def test_an_empty_answer_list_is_refused(client):
    assert client.post("/brand-dna/answers", json={"answers": []}).status_code == 422


def test_an_answer_to_an_unknown_question_is_refused(client):
    response = client.post(
        "/brand-dna/answers",
        json={"answers": [{"question_id": "q_not_a_question", "answer": "x"}]},
    )
    assert response.status_code == 422
    assert "q_not_a_question" in response.text


def test_completed_answers_render_the_brand_dna_the_gate_reads(client):
    assert answer_everything(client)["complete"] is True
    markdown = client.get("/brand-dna").json()["markdown"]
    for question in SEED_QUESTIONNAIRE.required_questions:
        assert f"- **{question.field}:**" in markdown


def test_the_gate_blocks_until_onboarding_is_complete_then_passes(client):
    client.post("/campaigns", json={"slug": SLUG})
    price = next(q for q in SEED_QUESTIONNAIRE.questions if q.field == "Price point")

    answer_everything(client, skip={price.id})
    blocked = client.get(f"/campaigns/{SLUG}/gate").json()
    assert blocked["ok"] is False
    assert any("Price point" in issue for issue in blocked["issues"])

    client.post(
        "/brand-dna/answers",
        json={"answers": [{"question_id": price.id, "answer": "$90 a month"}]},
    )
    assert client.get(f"/campaigns/{SLUG}/gate").json()["ok"] is True


def test_a_run_is_refused_while_required_fields_are_missing(client):
    client.post("/campaigns", json={"slug": SLUG})
    geography = next(
        q for q in SEED_QUESTIONNAIRE.questions if q.field == "Geography / service area"
    )
    answer_everything(client, skip={geography.id})
    response = client.post(f"/campaigns/{SLUG}/run", json={})
    assert response.status_code == 409
    assert any("Geography" in field for field in response.json()["missing_fields"])


def test_one_business_answers_are_invisible_to_another(client):
    from marketing_os.entrypoints.api.app import app, get_identity

    answer_everything(client)
    assert client.get("/brand-dna/completeness").json()["complete"] is True

    app.dependency_overrides[get_identity] = lambda: identity_for(OTHER_TENANT)
    other = client.get("/brand-dna").json()
    assert other["answers"] == []
    assert client.get("/brand-dna/completeness").json()["complete"] is False


def test_a_newer_question_set_prompts_rather_than_silently_blocking(client):
    from marketing_os.entrypoints.api.app import get_questionnaire_store
    from marketing_os.schemas import Question, Questionnaire

    answer_everything(client)
    added = Question(
        id="q_seasonality",
        field="Seasonality",
        section="Reach & constraints",
        text="When is your busiest season?",
        why_we_ask="Timing a campaign against demand changes what it should say.",
        help_text="Name the months, or say demand is steady.",
        required=True,
    )
    get_questionnaire_store().publish(
        Questionnaire(
            version=SEED_QUESTIONNAIRE.version + 1,
            published_at="2026-09-02T09:00:00Z",
            questions=[*SEED_QUESTIONNAIRE.questions, added],
        )
    )

    report = client.get("/brand-dna/completeness").json()
    assert report["unanswered_new_questions"] == ["q_seasonality"]
    assert [missing["field"] for missing in report["missing"]] == ["Seasonality"]
    assert client.get("/questionnaire").json()["version"] == SEED_QUESTIONNAIRE.version + 1

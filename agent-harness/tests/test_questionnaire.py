"""The questionnaire: the seeded question set, answer storage, and DNA rendering.

The question set is the single artifact driving the wizard, the rendered Brand
DNA and what the gate requires (ADR-0018), so these assert what an operator or
an API client can observe: which questions are asked, what a business's answers
render to, and what the completeness report names as missing.
"""

from __future__ import annotations

import pytest

from conftest import OTHER_TENANT, TENANT
from marketing_os.adapters.questionnaire import (
    InMemoryAnswerStore,
    InMemoryQuestionnaireStore,
)
from marketing_os.errors import ValidationError
from marketing_os.questionnaire import (
    SEED_QUESTIONNAIRE,
    completeness,
    render_brand_dna,
    required_dna_fields,
)
from marketing_os.schemas import BrandDnaRecord, DnaAnswer, Question, Questionnaire

"""Onboarding asks for facts, never for the artifacts the engine owes the
business. These are the phrasings that would mean a question had crossed the
line — asking the owner to author positioning, messaging, voice, or to pick
channels. Asking which channels they *already* use is a fact, and is allowed."""
CRAFTED_ARTIFACT_TERMS = (
    "value proposition",
    "customer promise",
    "differentiator",
    "positioning",
    "messaging",
    "brand voice",
    "tone of voice",
    "which channels should",
    "channels do you want",
)

REQUIRED_DNA_FIELDS = (
    "Business name",
    "What they sell",
    "Category / industry",
    "Price point",
    "Primary segment(s)",
    "Pain points / jobs-to-be-done",
    "Why customers choose them over alternatives",
    "Geography / service area",
    "Language(s)",
    "Budget range",
    "Hard constraints",
)


def answers_for(questionnaire: Questionnaire, *, skip: set[str] | None = None) -> BrandDnaRecord:
    """Build a record answering every Required question except the skipped ones.

    Args:
        questionnaire: The published question set to answer.
        skip: Question ids to leave unanswered.

    Returns:
        A Brand DNA record at the questionnaire's version.
    """
    omit = skip or set()
    return BrandDnaRecord(
        questionnaire_version=questionnaire.version,
        updated_at="2026-09-01T10:00:00Z",
        answers=[
            DnaAnswer(question_id=question.id, answer=f"Answer to {question.field}")
            for question in questionnaire.required_questions
            if question.id not in omit
        ],
    )


def test_seed_asks_for_every_required_dna_field():
    fields = {question.field for question in SEED_QUESTIONNAIRE.required_questions}
    assert set(REQUIRED_DNA_FIELDS) <= fields


def test_seed_asks_no_crafted_artifact_question():
    asked = " ".join(
        f"{question.field} {question.text}" for question in SEED_QUESTIONNAIRE.questions
    ).lower()
    for term in CRAFTED_ARTIFACT_TERMS:
        assert term not in asked, f"onboarding must not ask for '{term}' — the engine produces it"


def test_every_seed_question_explains_itself():
    for question in SEED_QUESTIONNAIRE.questions:
        assert question.why_we_ask.strip(), question.id
        assert question.help_text.strip(), question.id


def test_seed_question_ids_are_unique():
    ids = [question.id for question in SEED_QUESTIONNAIRE.questions]
    assert len(ids) == len(set(ids))


def test_required_dna_fields_come_from_the_published_question_set():
    assert required_dna_fields(SEED_QUESTIONNAIRE) == [
        question.field for question in SEED_QUESTIONNAIRE.required_questions
    ]


def test_completeness_is_complete_when_every_required_question_is_answered():
    report = completeness(SEED_QUESTIONNAIRE, answers_for(SEED_QUESTIONNAIRE))
    assert report.complete
    assert report.missing == []
    assert report.required_answered == report.required_total


def test_completeness_names_exactly_the_missing_required_fields():
    price = next(q for q in SEED_QUESTIONNAIRE.questions if q.field == "Price point")
    record = answers_for(SEED_QUESTIONNAIRE, skip={price.id})
    report = completeness(SEED_QUESTIONNAIRE, record)
    assert not report.complete
    assert [missing.field for missing in report.missing] == ["Price point"]
    assert report.missing[0].question_id == price.id
    assert report.missing[0].label == price.text


def test_completeness_treats_a_blank_answer_as_unanswered():
    record = answers_for(SEED_QUESTIONNAIRE)
    price = next(q for q in SEED_QUESTIONNAIRE.questions if q.field == "Price point")
    record.answers = [
        DnaAnswer(
            question_id=a.question_id,
            answer="   " if a.question_id == price.id else a.answer,
        )
        for a in record.answers
    ]
    report = completeness(SEED_QUESTIONNAIRE, record)
    assert [missing.field for missing in report.missing] == ["Price point"]


def test_a_newer_version_prompts_rather_than_silently_failing():
    added = Question(
        id="q_seasonality",
        field="Seasonality",
        section="Reach & constraints",
        text="When is your busiest season?",
        why_we_ask="Timing a campaign against demand changes what it should say.",
        help_text="Name the months, or say demand is steady.",
        required=True,
    )
    newer = Questionnaire(
        version=SEED_QUESTIONNAIRE.version + 1,
        published_at="2026-09-02T09:00:00Z",
        questions=[*SEED_QUESTIONNAIRE.questions, added],
    )
    report = completeness(
        newer, answers_for(SEED_QUESTIONNAIRE), answered_against=SEED_QUESTIONNAIRE
    )
    assert report.unanswered_new_questions == ["q_seasonality"]
    assert [missing.field for missing in report.missing] == ["Seasonality"]
    assert report.questionnaire_version == newer.version


def test_answers_to_a_retired_question_are_ignored():
    record = answers_for(SEED_QUESTIONNAIRE)
    record.answers.append(DnaAnswer(question_id="q_retired", answer="Old news"))
    report = completeness(SEED_QUESTIONNAIRE, record)
    assert report.complete


def test_rendered_dna_carries_every_answer_under_its_section():
    record = answers_for(SEED_QUESTIONNAIRE)
    markdown = render_brand_dna(SEED_QUESTIONNAIRE, record, business_name="Acme Climbing Gym")
    # Titled from the answer, not the passed identity name — see
    # test_rendered_dna_titles_itself_from_the_business_name_answer.
    assert markdown.startswith("# Brand DNA — Answer to Business name")
    for question in SEED_QUESTIONNAIRE.required_questions:
        assert f"- **{question.field}:** Answer to {question.field}" in markdown
        assert f"## {question.section}" in markdown or f"### {question.section}" in markdown


def test_rendered_dna_omits_unanswered_questions():
    price = next(q for q in SEED_QUESTIONNAIRE.questions if q.field == "Price point")
    record = answers_for(SEED_QUESTIONNAIRE, skip={price.id})
    markdown = render_brand_dna(SEED_QUESTIONNAIRE, record, business_name="Acme")
    assert "**Price point:**" not in markdown


def test_rendered_dna_indents_a_multi_line_answer_as_a_sub_list():
    record = BrandDnaRecord(
        questionnaire_version=SEED_QUESTIONNAIRE.version,
        answers=[DnaAnswer(question_id="q_what_they_sell", answer="Memberships\nIntro classes")],
    )
    markdown = render_brand_dna(SEED_QUESTIONNAIRE, record, business_name="Acme")
    assert "- **What they sell:**\n  - Memberships\n  - Intro classes" in markdown


def test_questionnaire_store_serves_the_seed_until_a_version_is_published():
    store = InMemoryQuestionnaireStore()
    assert store.published().version == SEED_QUESTIONNAIRE.version

    newer = SEED_QUESTIONNAIRE.model_copy(
        update={"version": SEED_QUESTIONNAIRE.version + 1, "published_at": "2026-09-02T09:00:00Z"}
    )
    store.publish(newer)
    assert store.published().version == newer.version


def test_publishing_an_older_version_is_refused():
    store = InMemoryQuestionnaireStore()
    older = SEED_QUESTIONNAIRE.model_copy(update={"version": SEED_QUESTIONNAIRE.version - 1})
    with pytest.raises(ValidationError):
        store.publish(older)


def test_answer_store_upserts_and_is_scoped_to_one_tenant():
    store = InMemoryAnswerStore()
    store.upsert(TENANT, version=1, answers=[DnaAnswer(question_id="q_price_point", answer="$50")])

    assert store.read(TENANT).answer_for("q_price_point") == "$50"
    assert store.read(OTHER_TENANT).answers == []

    store.upsert(TENANT, version=1, answers=[DnaAnswer(question_id="q_price_point", answer="$60")])
    record = store.read(TENANT)
    assert record.answer_for("q_price_point") == "$60"
    assert len(record.answers) == 1


def test_answer_store_records_the_version_answers_were_given_against():
    store = InMemoryAnswerStore()
    store.upsert(TENANT, version=3, answers=[DnaAnswer(question_id="q_business_name", answer="A")])
    assert store.read(TENANT).questionnaire_version == 3
    assert store.read(TENANT).updated_at is not None


def test_rendered_dna_titles_itself_from_the_business_name_answer():
    # The answers are the source of truth and the markdown a projection of them
    # (ADR-0018), so editing the Business name answer must move the heading too
    # rather than leaving it stating a second, stale name for the same business.
    record = answers_for(SEED_QUESTIONNAIRE)
    record.answers = [
        DnaAnswer(question_id="q_business_name", answer="Harbour Bikes & Cargo")
        if answer.question_id == "q_business_name"
        else answer
        for answer in record.answers
    ]
    markdown = render_brand_dna(SEED_QUESTIONNAIRE, record, business_name="Harbour Bikes")
    assert markdown.startswith("# Brand DNA — Harbour Bikes & Cargo")
    assert "- **Business name:** Harbour Bikes & Cargo" in markdown


def test_rendered_dna_falls_back_to_the_identity_name_when_unanswered():
    business = next(q for q in SEED_QUESTIONNAIRE.questions if q.id == "q_business_name")
    record = answers_for(SEED_QUESTIONNAIRE, skip={business.id})
    markdown = render_brand_dna(SEED_QUESTIONNAIRE, record, business_name="Harbour Bikes")
    assert markdown.startswith("# Brand DNA — Harbour Bikes")

"""The questionnaire: the seeded question set, answer storage, and DNA rendering.

The question set is the single artifact driving the wizard, the rendered Brand
DNA and what the gate requires (ADR-0018), so these assert what an operator or
an API client can observe: which questions are asked, what a business's answers
render to, and what the completeness report names as missing.
"""

from __future__ import annotations

import pytest

from conftest import OTHER_TENANT, TENANT, answered_clarifications
from marketing_os.adapters.questionnaire import (
    InMemoryAnswerStore,
    InMemoryQuestionnaireStore,
)
from marketing_os.errors import DocumentNotFoundError, ValidationError
from marketing_os.questionnaire import (
    CLARIFICATIONS_HEADING,
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
    # A save refuses a blank now, so this only reaches the report from a row
    # stored before that rule — which is exactly what it must survive.
    record = answers_for(SEED_QUESTIONNAIRE)
    price = next(q for q in SEED_QUESTIONNAIRE.questions if q.field == "Price point")
    record.answers = [
        DnaAnswer(question_id=a.question_id, answer="   ") if a.question_id == price.id else a
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


def test_answer_store_removes_one_answer_and_leaves_the_rest():
    store = InMemoryAnswerStore()
    store.upsert(
        TENANT,
        version=1,
        answers=[
            DnaAnswer(question_id="q_business_name", answer="Acme"),
            DnaAnswer(question_id="q_price_point", answer="$50"),
        ],
    )

    store.remove(TENANT, question_id="q_price_point")

    record = store.read(TENANT)
    assert record.answer_for("q_price_point") is None
    assert record.answer_for("q_business_name") == "Acme"


def test_answer_store_removal_does_not_advance_the_last_saved_time():
    # `updated_at` says when an answer was last saved. A removal writes nothing,
    # so it must not read as a save — and both adapters must agree on that.
    store = InMemoryAnswerStore()
    store.upsert(
        TENANT,
        version=1,
        answers=[
            DnaAnswer(question_id="q_business_name", answer="Acme"),
            DnaAnswer(question_id="q_price_point", answer="$50"),
        ],
    )
    saved_at = store.read(TENANT).updated_at

    assert store.remove(TENANT, question_id="q_price_point").updated_at == saved_at


def test_answer_store_removing_an_unanswered_question_changes_nothing():
    store = InMemoryAnswerStore()
    store.upsert(TENANT, version=1, answers=[DnaAnswer(question_id="q_price_point", answer="$50")])

    store.remove(TENANT, question_id="q_business_name")

    assert store.read(TENANT).answer_for("q_price_point") == "$50"


def test_answer_store_removal_is_scoped_to_one_tenant():
    store = InMemoryAnswerStore()
    store.upsert(TENANT, version=1, answers=[DnaAnswer(question_id="q_price_point", answer="$50")])
    store.upsert(
        OTHER_TENANT, version=1, answers=[DnaAnswer(question_id="q_price_point", answer="$90")]
    )

    store.remove(OTHER_TENANT, question_id="q_price_point")

    assert store.read(TENANT).answer_for("q_price_point") == "$50"


def test_a_stored_blank_answer_is_still_readable():
    # The shipped code could store a blank answer, so such rows exist. Reading
    # one back must keep working — the rule refusing new blanks belongs on the
    # way in, not on the shape a stored answer is read as.
    record = BrandDnaRecord(
        questionnaire_version=SEED_QUESTIONNAIRE.version,
        answers=[DnaAnswer(question_id="q_price_point", answer="   ")],
    )
    assert record.answer_for("q_price_point") == "   "


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


def test_the_ask_tool_states_the_questionnaire_rule():
    """ADR-0028: the rule is checked in both places it is stated.

    The questionnaire is checked above by what it asks; the tool is checked by
    what it tells the specialist, since its questions are written at run time.
    """
    from marketing_os.adapters.tools.clarify import ask_tenant_tool

    description = ask_tenant_tool().description.lower()
    assert "uniquely knows" in description
    for term in ("positioning", "messaging", "channel"):
        assert term in description, f"the tool must forbid asking for '{term}'"
    assert "never" in description


EMAIL_LIST = answered_clarifications("performance-plan", "summer-push")[0]
"""One answered Clarification, as the performance plan of one campaign asked it."""


def test_rendered_dna_carries_clarifications_under_their_own_section_after_the_questionnaire():
    record = answers_for(SEED_QUESTIONNAIRE)
    record.clarifications.append(EMAIL_LIST)

    markdown = render_brand_dna(SEED_QUESTIONNAIRE, record, business_name="Acme")

    assert CLARIFICATIONS_HEADING == "## Clarifications"
    section = markdown.index(CLARIFICATIONS_HEADING)
    assert section > markdown.index("Hard constraints")
    body = markdown[section:]
    assert f"### {EMAIL_LIST.question}" in body
    assert f"> {EMAIL_LIST.answer}" in body
    assert EMAIL_LIST.reason in body
    assert "performance-plan" in body
    assert "summer-push" in body


def test_rendered_dna_has_no_clarifications_section_until_one_is_answered():
    markdown = render_brand_dna(
        SEED_QUESTIONNAIRE, answers_for(SEED_QUESTIONNAIRE), business_name="Acme"
    )
    assert CLARIFICATIONS_HEADING not in markdown


def test_clarifications_never_count_toward_completeness():
    """The gate and the report ignore them: a specialist's question never locks the business out."""
    price = next(q for q in SEED_QUESTIONNAIRE.questions if q.field == "Price point")
    incomplete = answers_for(SEED_QUESTIONNAIRE, skip={price.id})
    incomplete.clarifications.extend([EMAIL_LIST, EMAIL_LIST.model_copy(update={"id": "clr_2"})])
    complete = answers_for(SEED_QUESTIONNAIRE)
    complete.clarifications.append(EMAIL_LIST)

    assert completeness(SEED_QUESTIONNAIRE, incomplete) == completeness(
        SEED_QUESTIONNAIRE, answers_for(SEED_QUESTIONNAIRE, skip={price.id})
    )
    assert completeness(SEED_QUESTIONNAIRE, complete) == completeness(
        SEED_QUESTIONNAIRE, answers_for(SEED_QUESTIONNAIRE)
    )


def test_answer_store_keeps_clarifications_beside_the_answers_and_scoped_to_one_tenant():
    store = InMemoryAnswerStore()
    store.upsert(TENANT, version=1, answers=[DnaAnswer(question_id="q_price_point", answer="$50")])

    record = store.add_clarifications(TENANT, clarifications=[EMAIL_LIST])

    assert record.clarifications == [EMAIL_LIST]
    assert record.answer_for("q_price_point") == "$50"
    assert store.read(TENANT).clarifications == [EMAIL_LIST]
    assert store.read(OTHER_TENANT).clarifications == []


def test_answer_store_appends_clarifications_in_the_order_they_were_answered():
    store = InMemoryAnswerStore()
    second = EMAIL_LIST.model_copy(update={"id": "clr_2", "question": "How big is it?"})
    store.add_clarifications(TENANT, clarifications=[EMAIL_LIST])

    store.add_clarifications(TENANT, clarifications=[second])

    assert [item.id for item in store.read(TENANT).clarifications] == ["clr_0", "clr_2"]


def test_saving_a_questionnaire_answer_leaves_the_clarifications_alone():
    store = InMemoryAnswerStore()
    store.add_clarifications(TENANT, clarifications=[EMAIL_LIST])

    store.upsert(TENANT, version=1, answers=[DnaAnswer(question_id="q_price_point", answer="$50")])
    store.remove(TENANT, question_id="q_price_point")

    assert store.read(TENANT).clarifications == [EMAIL_LIST]


def test_answer_store_edits_one_clarification_answer_and_leaves_the_rest():
    """A retrospective correction changes the answer, the time it was given, and nothing else."""
    store = InMemoryAnswerStore()
    second = EMAIL_LIST.model_copy(update={"id": "clr_2", "question": "How big is it?"})
    store.upsert(TENANT, version=1, answers=[DnaAnswer(question_id="q_price_point", answer="$50")])
    store.add_clarifications(TENANT, clarifications=[EMAIL_LIST, second])

    record = store.update_clarification(
        TENANT, clarification_id=EMAIL_LIST.id, answer="No list yet; we collect emails at the desk."
    )

    edited, kept = record.clarifications
    assert edited.answer == "No list yet; we collect emails at the desk."
    assert edited.answered_at != EMAIL_LIST.answered_at
    assert edited.model_dump(exclude={"answer", "answered_at"}) == EMAIL_LIST.model_dump(
        exclude={"answer", "answered_at"}
    )
    assert kept == second
    assert record.answer_for("q_price_point") == "$50"
    assert store.read(TENANT).clarifications == [edited, kept]


def test_answer_store_refuses_to_edit_a_clarification_the_business_does_not_have():
    """Another business's Clarification reads as missing, and nothing of theirs changes."""
    store = InMemoryAnswerStore()
    store.add_clarifications(TENANT, clarifications=[EMAIL_LIST])

    with pytest.raises(DocumentNotFoundError):
        store.update_clarification(TENANT, clarification_id="clr_missing", answer="x")
    with pytest.raises(DocumentNotFoundError):
        store.update_clarification(OTHER_TENANT, clarification_id=EMAIL_LIST.id, answer="x")

    assert store.read(TENANT).clarifications == [EMAIL_LIST]
    assert store.read(OTHER_TENANT).clarifications == []

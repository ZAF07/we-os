"""What stands between a business and starting work, derived from the question set.

Pure functions over a published :class:`~marketing_os.schemas.Questionnaire` and
a tenant's answers. Nothing here reads a store, so the DNA Gate, the API's
completeness endpoint and the wizard's progress all compute the same answer from
the same two inputs.

Required-ness is the question set's to decide, so publishing a version with a new
Required question tightens the gate with no code change (ADR-0018). A business
whose answers predate that version is **prompted** with the new question ids
rather than silently failing a gate that moved under them.
"""

from __future__ import annotations

from marketing_os.schemas import BrandDnaRecord, DnaCompleteness, MissingField, Questionnaire


def required_dna_fields(questionnaire: Questionnaire) -> list[str]:
    """Return the Brand DNA field labels the published question set makes Required.

    Args:
        questionnaire: The published question set.

    Returns:
        The Required fields, in the order the questionnaire asks for them.
    """
    return [question.field for question in questionnaire.required_questions]


def _is_answered(record: BrandDnaRecord, question_id: str) -> bool:
    """Return whether a question has a non-blank answer.

    Args:
        record: The tenant's Brand DNA answers.
        question_id: The question to check.

    Returns:
        ``True`` when an answer exists and is not only whitespace.
    """
    answer = record.answer_for(question_id)
    return bool(answer and answer.strip())


def completeness(
    questionnaire: Questionnaire,
    record: BrandDnaRecord,
    *,
    answered_against: Questionnaire | None = None,
) -> DnaCompleteness:
    """Report which Required fields a business still owes, and what is newly asked.

    Args:
        questionnaire: The published question set the report is computed against.
        record: The tenant's stored answers and the version they were given against.
        answered_against: The version the business actually answered, when it is
            still retrievable. A question is "new" only when the business was
            never shown it; without the older version, every unanswered question
            on a superseded record is treated as new, which over-prompts rather
            than under-prompts.

    Returns:
        The completeness report, naming every missing Required field and every
        question a newer published version added that this business's answers
        predate.
    """
    required = questionnaire.required_questions
    missing = [
        MissingField(question_id=question.id, field=question.field, label=question.text)
        for question in required
        if not _is_answered(record, question.id)
    ]
    newly_asked: list[str] = []
    if record.questionnaire_version < questionnaire.version:
        previously_asked = (
            {question.id for question in answered_against.questions} if answered_against else set()
        )
        newly_asked = [
            question.id
            for question in questionnaire.questions
            if question.id not in previously_asked and not _is_answered(record, question.id)
        ]
    return DnaCompleteness(
        complete=not missing,
        questionnaire_version=questionnaire.version,
        required_total=len(required),
        required_answered=len(required) - len(missing),
        missing=missing,
        unanswered_new_questions=newly_asked,
    )

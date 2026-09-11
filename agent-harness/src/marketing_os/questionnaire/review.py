"""When a business is due to look at its Brand DNA again (ADR-0028).

Facts about a business drift, so the platform asks the owner to review their
Brand DNA and their Clarifications on an interval. Whether a review is due is
derived from one timestamp on every read and never stored, so the item on Home
and the reminder email can never disagree with each other or with the truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from marketing_os.ports import AnswerStore, QuestionnaireStore
from marketing_os.questionnaire.completeness import completeness


@dataclass(frozen=True)
class DnaReview:
    """Whether a business's Brand DNA is due a review, and what that rests on.

    Attributes:
        reviewed_at: When the DNA was last reviewed — the recorded review, or
            when its answers were last saved for a business that has never
            marked one. ``None`` when there is no DNA to review.
        due: Whether more than the interval has passed since then.
    """

    reviewed_at: datetime | None
    due: bool


def dna_review(
    *,
    reviewed_at: datetime | None,
    dna_updated_at: datetime | None,
    complete: bool,
    now: datetime,
    interval: timedelta,
) -> DnaReview:
    """Decide whether a business's Brand DNA is due a review.

    A business that has never marked a review counts from when its answers
    were last saved, which for a tenant seeded or migrated without a recorded
    review is the closest thing to when its DNA was completed. An incomplete
    DNA is never due: it is owed answers, which the Setup item already stands
    for, and a Review beside it would be noise.

    Args:
        reviewed_at: The review the tenant record holds, if any.
        dna_updated_at: When the business's answers were last saved, if ever.
        complete: Whether every Required question is answered.
        now: The current time.
        interval: How long a review holds for.

    Returns:
        The review, due when the DNA is complete and more than ``interval``
        has passed since it was last reviewed.
    """
    last_reviewed = reviewed_at or dna_updated_at
    due = complete and last_reviewed is not None and now - last_reviewed > interval
    return DnaReview(reviewed_at=last_reviewed, due=due)


def review_from_stores(
    tenant_id: str,
    *,
    reviewed_at: datetime | None,
    answers: AnswerStore,
    questionnaires: QuestionnaireStore,
    now: datetime,
    interval: timedelta,
) -> DnaReview:
    """Decide whether a business's Brand DNA is due a review, from what is stored.

    The one place the stored facts are gathered into the judgement, so the API
    that shows the Review item and the task that sends the reminder read the
    same answer.

    Args:
        tenant_id: The tenant whose DNA to judge.
        reviewed_at: The review the tenant record holds, if any.
        answers: The store holding the business's answers.
        questionnaires: The store holding the published question set.
        now: The current time.
        interval: How long a review holds for.

    Returns:
        The review.
    """
    published = questionnaires.published()
    record = answers.read(tenant_id)
    answered_against = questionnaires.version(record.questionnaire_version)
    report = completeness(published, record, answered_against=answered_against)
    return dna_review(
        reviewed_at=reviewed_at,
        dna_updated_at=(datetime.fromisoformat(record.updated_at) if record.updated_at else None),
        complete=report.complete,
        now=now,
        interval=interval,
    )


def reminder_due(
    review: DnaReview, *, reminded_at: datetime | None, now: datetime, interval: timedelta
) -> bool:
    """Decide whether a business should be emailed that its review is due.

    Once per review interval: a business hears about a due review when it has
    never been reminded, or when the last reminder is older than the interval.
    A review that is not due is never reminded about, however long ago the
    last reminder went out.

    Args:
        review: Whether the review is due.
        reminded_at: When the business was last reminded, if ever.
        now: The current time.
        interval: How long a reminder holds for — the review interval.

    Returns:
        ``True`` when a reminder should be sent now.
    """
    if not review.due:
        return False
    return reminded_at is None or now - reminded_at > interval

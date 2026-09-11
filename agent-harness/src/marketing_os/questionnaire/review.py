"""When a business is due to look at its Brand DNA again (ADR-0028).

Facts about a business drift, so the platform asks the owner to review their
Brand DNA and their Clarifications on an interval. Whether a review is due is
derived from one timestamp on every read and never stored, so the item on Home
and the reminder email can never disagree with each other or with the truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


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

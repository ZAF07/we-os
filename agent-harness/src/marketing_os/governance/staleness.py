"""Downstream staleness — which deliverables now rest on a superseded decision.

Campaigns get edited weeks later, after work has been built on top of them. When
a business owner re-opens a stage they had approved, everything downstream was
produced from the decision they just changed. That work is **stale**: it is not
regenerated, it is flagged, and the owner re-runs it when they are ready
(ADR-0015). Auto-re-running was rejected — it burns tokens and image spend on
work nobody asked to have redone — so staleness is what makes the inconsistency
visible and the owner's to resolve.

Staleness is **derived, never stored**. A deliverable is stale when an upstream
stage's newest version was written after it, so the flag is a comparison over the
version chain rather than a column that must be written in the same breath as
every re-run and can therefore drift out of step with it. Re-opening a stage
appends a version to it, which is what makes everything downstream mechanically
older than its input.

The comparison is on each version's campaign-wide ``sequence``, not on its
``created_at``. A wall clock cannot answer this question reliably: timestamps tie
at microsecond resolution under rapid writes, and Postgres ``now()`` is fixed for
a whole transaction, so two versions written together would compare equal and the
staleness would silently vanish — the exact failure the flag exists to prevent.
"""

from __future__ import annotations

from marketing_os.governance.pipeline import PIPELINE
from marketing_os.ports import DeliverableStore
from marketing_os.schemas import DeliverableVersion


def stale_stages(store: DeliverableStore, tenant: str, slug: str) -> list[str]:
    """Return the stages whose deliverable rests on a decision revised since.

    Walks the pipeline in order carrying the highest upstream write order seen so
    far. A stage written before that point was built on an input that has since
    changed, so it is stale; a stage written after it is current, and becomes the
    new watermark for everything below.

    A stage that has produced nothing is never stale — staleness describes work
    that exists and has been superseded, not work that was never done.

    Args:
        store: The store holding each stage's version chain.
        tenant: The tenant that owns the campaign.
        slug: The campaign slug.

    Returns:
        The stale stage keys in mandatory pipeline order, empty when every
        deliverable is current.
    """
    latest = {
        stage.key: version
        for stage in PIPELINE
        if (version := store.latest(tenant, slug, stage.key)) is not None
    }
    return sorted(stale_from_latest(latest), key=[stage.key for stage in PIPELINE].index)


def stale_from_latest(latest: dict[str, DeliverableVersion]) -> set[str]:
    """Return the stale stages among deliverables that have already been read.

    The same walk :func:`stale_stages` performs, over versions a caller read for
    itself — so listing a portfolio can read every campaign at once and still
    decide staleness by this one rule.

    Args:
        latest: The newest version of each stage that has produced one, keyed by
            stage key; stages that produced nothing are simply absent.

    Returns:
        The stale stage keys, empty when every deliverable is current.
    """
    stale: set[str] = set()
    newest_upstream = 0
    for stage in PIPELINE:
        version = latest.get(stage.key)
        if version is None:
            continue
        if version.sequence < newest_upstream:
            stale.add(stage.key)
        else:
            newest_upstream = version.sequence
    return stale

"""Campaign progress — how far a campaign has got, and what its situation is.

"Where has this campaign got to?" is the question the product exists to answer,
and it is two questions on separate axes (ADR-0017): each **stage** has a state
saying how far it got, and the **campaign** has a lifecycle status saying what
its situation is. A campaign waiting on a person is ``awaiting_approval``
whichever stage it is holding at.

Both are derived from the deliverables themselves — their version chains and
their write order — rather than from anything rendered for an interface, so the
answer cannot drift from the work it describes by way of a presentation change.
The rule that a stale stage un-approves a whole campaign (ADR-0015) lives here
for the same reason: it is a decision about the business's work, not about HTTP.

Stores arrive as parameters. Nothing here reads a request, and nothing returns
an HTTP shape — the driving adapter shapes the response from these values.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from marketing_os.governance.pipeline import PIPELINE, Stage, apply_approval_policies
from marketing_os.governance.staleness import stale_stages
from marketing_os.ports import DeliverableStore
from marketing_os.schemas import DeliverableVersion

DRAFT = "draft"
RUNNING = "running"
AWAITING_APPROVAL = "awaiting_approval"
APPROVED = "approved"
"""The campaign lifecycle statuses.

``running`` and ``awaiting_approval`` are spelled the same as the *run* statuses
in :mod:`marketing_os.adapters.runs`, and deliberately defined separately: a run
and a campaign are different axes (ADR-0017). A campaign with no live run at all
can still read ``running``, and the day one axis gains a status the other does
not, these must be free to diverge without an adapter's constant following.
"""

PENDING = "pending"
COMPLETED = "completed"
STALE = "stale"
"""The per-stage states, saying how far one stage has got."""


@dataclass(frozen=True)
class StageProgress:
    """How far one stage has got, and what the system will do when it gets there.

    Attributes:
        stage: The pipeline stage, carrying its configured approval policy.
        state: ``pending``, ``completed``, ``awaiting_approval`` or ``stale``.
        latest: The newest version of its deliverable, or ``None`` when the
            stage has produced nothing.
        stale: Whether the stage rests on a decision re-opened since it ran. A
            stage holding at a gate reports ``awaiting_approval`` as its state
            even when this is ``True``, so both are carried: the state says what
            the person must decide next, this says what the work rests on.
    """

    stage: Stage
    state: str
    latest: DeliverableVersion | None
    stale: bool


@dataclass(frozen=True)
class CampaignProgress:
    """A campaign's lifecycle status and the state of every stage under it.

    Attributes:
        status: ``draft``, ``running``, ``awaiting_approval`` or ``approved``.
        stages: Every stage in mandatory pipeline order.
    """

    status: str
    stages: list[StageProgress]


def campaign_status(produced: set[str], stale: set[str], waiting: str | None) -> str:
    """Return the campaign's lifecycle status, a separate axis from stage progress.

    Lifecycle answers "what is this campaign's situation?" while stage state
    answers "how far has it got?" (ADR-0017), so a campaign waiting on a person
    is ``awaiting_approval`` whichever stage it is holding at.

    A campaign is only ``approved`` once every stage has produced a deliverable
    **and none of them is stale**. That is the criterion that stops re-opening a
    decision leaving the campaign looking signed off while creative underneath it
    rests on strategy the owner has since replaced (ADR-0015).

    Args:
        produced: The stages that have produced a deliverable.
        stale: The stages resting on a decision that has since been re-opened.
        waiting: The stage holding at an Approval Gate, if any.

    Returns:
        One of ``draft``, ``running``, ``awaiting_approval`` or ``approved``.
    """
    if waiting is not None:
        return AWAITING_APPROVAL
    if not produced:
        return DRAFT
    if stale or len(produced) < len(PIPELINE):
        return RUNNING
    return APPROVED


def stage_progress(
    stage: Stage, latest: DeliverableVersion | None, waiting: str | None, stale: set[str]
) -> StageProgress:
    """Describe how far one stage has got.

    A stage holding at a gate reports ``awaiting_approval`` even when its
    deliverable is stale: what the person must do next is decide on the draft in
    front of them, and reporting the stage as stale instead would hide the
    decision the run is actually blocked on.

    Args:
        stage: The pipeline stage, carrying its configured approval policy.
        latest: The newest version of its deliverable, if it has produced one.
        waiting: The stage currently halted at an Approval Gate, if any.
        stale: The stages resting on a decision that has since been re-opened.

    Returns:
        The stage's progress.
    """
    if stage.key == waiting:
        state = AWAITING_APPROVAL
    elif stage.key in stale:
        state = STALE
    elif latest is not None:
        state = COMPLETED
    else:
        state = PENDING
    return StageProgress(
        stage=stage,
        state=state,
        latest=latest,
        stale=stage.key in stale,
    )


async def campaign_progress(
    deliverables: DeliverableStore,
    tenant: str,
    slug: str,
    *,
    human_gate_stages: list[str] | None,
    awaiting_stage: Callable[[], Awaitable[str | None]],
) -> CampaignProgress:
    """Report a campaign's stages and the lifecycle status derived from them.

    The single place staleness is resolved for a campaign, so the stage states,
    the lifecycle status, and anything an interface derives from either cannot
    come to different answers about the same work.

    Args:
        deliverables: The store holding each stage's version chain.
        tenant: The tenant that owns the campaign.
        slug: The campaign slug.
        human_gate_stages: The stage keys configured to halt at an Approval
            Gate, or ``None`` to keep each stage's shipped policy (ADR-0015).
        awaiting_stage: Resolves the stage a live run is halted at, or ``None``
            when none is. Taken as a callable because answering it means asking
            the run registry and the checkpointer — a different concern from
            reading deliverables, and one the caller already owns.

    Returns:
        The campaign's lifecycle status and every stage in pipeline order.
    """
    configured = apply_approval_policies(PIPELINE, human_gate_stages)
    waiting = await awaiting_stage()
    stale = stale_keys(deliverables, tenant, slug)
    latest = {stage.key: deliverables.latest(tenant, slug, stage.key) for stage in configured}
    produced = {key for key, version in latest.items() if version is not None}
    return CampaignProgress(
        status=campaign_status(produced, stale, waiting),
        stages=[stage_progress(stage, latest[stage.key], waiting, stale) for stage in configured],
    )


@dataclass(frozen=True)
class DeliverableProgress:
    """One produced deliverable, and whether the work under it still holds.

    Attributes:
        stage_key: The stage that produced it.
        latest: The newest version.
        stale: Whether it rests on a decision re-opened since it was written.
    """

    stage_key: str
    latest: DeliverableVersion
    stale: bool


def produced_deliverables(
    deliverables: DeliverableStore, tenant: str, slug: str
) -> list[DeliverableProgress]:
    """Report every deliverable a campaign has produced, in pipeline order.

    Args:
        deliverables: The store holding each stage's version chain.
        tenant: The tenant that owns the campaign.
        slug: The campaign slug.

    Returns:
        One entry per stage that has produced a deliverable; stages that have
        produced nothing are absent rather than reported empty.
    """
    stale = stale_keys(deliverables, tenant, slug)
    produced: list[DeliverableProgress] = []
    for stage_key in deliverables.stages(tenant, slug):
        latest = deliverables.latest(tenant, slug, stage_key)
        if latest is None:
            continue
        produced.append(
            DeliverableProgress(stage_key=stage_key, latest=latest, stale=stage_key in stale)
        )
    return produced


def stale_keys(deliverables: DeliverableStore, tenant: str, slug: str) -> set[str]:
    """Return the stages of a campaign resting on a decision re-opened since.

    Args:
        deliverables: The store holding each stage's version chain.
        tenant: The tenant that owns the campaign.
        slug: The campaign slug.

    Returns:
        The stale stage keys, empty when every deliverable is current.
    """
    return set(stale_stages(deliverables, tenant, slug))

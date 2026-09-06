"""Campaign progress: how far a campaign has got, and what its situation is.

Two axes, deliberately separate (ADR-0017): a **stage** state says how far one
stage got, a **campaign** status says what the whole campaign's situation is.
Driven directly against :mod:`marketing_os.campaign.progress` rather than over
HTTP, because where a campaign has got to is a fact about the business's work —
the seam these tests exist to keep honest is the one where that stops depending
on a web framework.
"""

from __future__ import annotations

from conftest import SLUG, TENANT
from marketing_os.adapters.deliverables import InMemoryDeliverableStore
from marketing_os.campaign.progress import (
    APPROVED,
    AWAITING_APPROVAL,
    COMPLETED,
    DRAFT,
    PENDING,
    RUNNING,
    STALE,
    campaign_progress,
    campaign_status,
    produced_deliverables,
    stale_keys,
)
from marketing_os.governance.pipeline import PIPELINE

ALL_STAGES = [stage.key for stage in PIPELINE]


def _store(*stage_keys: str) -> InMemoryDeliverableStore:
    """Build a store where each named stage has produced one deliverable.

    Written in the order given, so writing an upstream stage last is what makes
    everything after it stale.

    Args:
        *stage_keys: The stages to write, in write order.

    Returns:
        The populated store.
    """
    store = InMemoryDeliverableStore()
    for stage_key in stage_keys:
        store.append(TENANT, SLUG, stage_key, f"# {stage_key}\n")
    return store


async def _progress_of(store: InMemoryDeliverableStore, *, waiting: str | None = None):
    """Report a campaign's progress from a store, naming what is waiting.

    Args:
        store: The deliverable store to read.
        waiting: The stage a live run is holding at, or ``None``.

    Returns:
        The campaign's progress.
    """

    async def waiting_stage() -> str | None:
        return waiting

    return await campaign_progress(
        store,
        TENANT,
        SLUG,
        human_gate_stages=None,
        awaiting_stage=waiting_stage,
    )


def test_a_campaign_that_has_produced_nothing_is_a_draft() -> None:
    assert campaign_status(produced=set(), stale=set(), waiting=None) == DRAFT


def test_a_campaign_waiting_on_a_person_says_so_whatever_else_is_true() -> None:
    """Lifecycle is its own axis: the gate wins over how far the stages got."""
    every_stage = set(ALL_STAGES)

    assert campaign_status(every_stage, stale=set(), waiting="research") == AWAITING_APPROVAL
    assert campaign_status(set(), stale=set(), waiting="research") == AWAITING_APPROVAL
    assert campaign_status(every_stage, {"research"}, waiting="research") == AWAITING_APPROVAL


def test_a_campaign_part_way_through_the_pipeline_is_running() -> None:
    assert campaign_status({"research"}, stale=set(), waiting=None) == RUNNING


def test_a_campaign_is_approved_only_once_every_stage_has_produced_current_work() -> None:
    assert campaign_status(set(ALL_STAGES), stale=set(), waiting=None) == APPROVED


def test_stale_work_un_approves_a_finished_campaign() -> None:
    """Re-opening a decision must not leave the campaign looking signed off.

    The criterion from ADR-0015: creative resting on strategy the owner has
    since replaced is not approved work, however complete it looks.
    """
    assert campaign_status(set(ALL_STAGES), {"brand-strategy"}, waiting=None) == RUNNING


async def test_a_stage_that_has_produced_nothing_is_pending() -> None:
    progress = await _progress_of(_store())

    assert {stage.state for stage in progress.stages} == {PENDING}
    assert all(stage.latest is None for stage in progress.stages)


async def test_a_stage_that_has_produced_current_work_is_completed() -> None:
    progress = await _progress_of(_store("research"))

    research = next(stage for stage in progress.stages if stage.stage.key == "research")
    assert research.state == COMPLETED
    assert research.latest is not None
    assert research.latest.version == 1


async def test_a_stage_resting_on_a_reopened_decision_is_stale() -> None:
    """Writing an upstream stage after a downstream one supersedes it."""
    progress = await _progress_of(_store("research", "brand-strategy", "research"))

    states = {stage.stage.key: stage.state for stage in progress.stages}
    assert states["brand-strategy"] == STALE
    assert states["research"] == COMPLETED


async def test_a_stage_at_a_gate_reports_the_decision_not_its_staleness() -> None:
    """What the person must do next is decide on the draft in front of them.

    Reporting the stage as stale instead would hide the decision the run is
    actually blocked on — so the state says ``awaiting_approval`` while the
    ``stale`` flag still carries what the work rests on.
    """
    store = _store("research", "brand-strategy", "research")

    progress = await _progress_of(store, waiting="brand-strategy")

    held = next(stage for stage in progress.stages if stage.stage.key == "brand-strategy")
    assert held.state == AWAITING_APPROVAL
    assert held.stale, "the stage is still resting on a superseded decision"


async def test_every_stage_is_reported_in_mandatory_pipeline_order() -> None:
    progress = await _progress_of(_store("research"))

    assert [stage.stage.key for stage in progress.stages] == ALL_STAGES


def test_only_stages_that_produced_something_are_reported_as_deliverables() -> None:
    produced = produced_deliverables(_store("research", "brand-strategy"), TENANT, SLUG)

    assert [item.stage_key for item in produced] == ["research", "brand-strategy"]
    assert all(item.latest.version == 1 for item in produced)
    assert not any(item.stale for item in produced)


def test_a_superseded_deliverable_is_reported_stale() -> None:
    produced = produced_deliverables(_store("research", "brand-strategy", "research"), TENANT, SLUG)

    stale = {item.stage_key for item in produced if item.stale}
    assert stale == {"brand-strategy"}


def test_nothing_is_stale_in_a_campaign_written_in_pipeline_order() -> None:
    assert stale_keys(_store("research", "brand-strategy"), TENANT, SLUG) == set()

"""Pipeline: order, ownership, and deliverable-exists gating."""

from __future__ import annotations

from conftest import SLUG, TENANT
from marketing_os.adapters.documents import FilesystemDocumentStore
from marketing_os.governance import PIPELINE, prerequisite_met
from marketing_os.governance.pipeline import DIRECTOR, PIPELINE_BY_KEY, stage_document


def test_pipeline_order_is_mandatory():
    assert [s.key for s in PIPELINE] == [
        "research",
        "brand-strategy",
        "campaign-strategy",
        "performance-plan",
        "creative-brief",
        "asset-prompts",
    ]


def test_prerequisite_chain_follows_the_order():
    assert PIPELINE_BY_KEY["performance-plan"].prerequisite == "campaign-strategy.md"
    assert PIPELINE_BY_KEY["creative-brief"].prerequisite == "performance-plan.md"
    assert PIPELINE_BY_KEY["asset-prompts"].prerequisite == "creative-brief.md"


def test_campaign_strategy_is_director_owned():
    assert PIPELINE_BY_KEY["campaign-strategy"].agent == DIRECTOR
    assert PIPELINE_BY_KEY["research"].agent == "market-research"


def test_performance_plan_task_asks_for_channels_spend_kpis_and_placements():
    task = PIPELINE_BY_KEY["performance-plan"].task
    assert "channel mix" in task
    assert "per-channel spend allocation" in task
    assert "KPI targets" in task
    assert "placement" in task


def test_creative_brief_task_briefs_against_the_plans_placements():
    task = PIPELINE_BY_KEY["creative-brief"].task
    assert "performance plan" in task
    assert "placements" in task


def test_first_stage_has_no_prerequisite(settings):
    store = FilesystemDocumentStore(settings.root)
    research = PIPELINE_BY_KEY["research"]
    assert prerequisite_met(store, TENANT, SLUG, research) is True


def test_stage_blocked_until_prerequisite_exists(settings):
    store = FilesystemDocumentStore(settings.root)
    brand = PIPELINE_BY_KEY["brand-strategy"]
    # research.md does not exist yet -> blocked
    assert prerequisite_met(store, TENANT, SLUG, brand) is False
    # create the prerequisite deliverable -> unblocked
    store.write(TENANT, f"campaigns/{SLUG}/research.md", "findings")
    assert prerequisite_met(store, TENANT, SLUG, brand) is True


def test_creative_brief_blocked_until_performance_plan_exists(settings):
    store = FilesystemDocumentStore(settings.root)
    brief = PIPELINE_BY_KEY["creative-brief"]
    assert prerequisite_met(store, TENANT, SLUG, brief) is False
    store.write(TENANT, f"campaigns/{SLUG}/performance-plan.md", "plan")
    assert prerequisite_met(store, TENANT, SLUG, brief) is True


def test_stage_document_is_the_tenant_relative_path():
    research = PIPELINE_BY_KEY["research"]
    assert stage_document(SLUG, research) == "campaigns/acme/research.md"

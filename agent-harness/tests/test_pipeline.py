"""Pipeline: order, ownership, and deliverable-exists gating."""

from __future__ import annotations

from marketing_os.governance import PIPELINE, deliverable_path, prerequisite_met
from marketing_os.governance.pipeline import DIRECTOR, PIPELINE_BY_KEY


def test_pipeline_order_is_mandatory():
    assert [s.key for s in PIPELINE] == [
        "research",
        "brand-strategy",
        "campaign-strategy",
        "creative-brief",
        "asset-prompts",
        "performance-plan",
    ]


def test_campaign_strategy_is_director_owned():
    assert PIPELINE_BY_KEY["campaign-strategy"].agent == DIRECTOR
    assert PIPELINE_BY_KEY["research"].agent == "market-research"


def test_first_stage_has_no_prerequisite(settings):
    research = PIPELINE_BY_KEY["research"]
    assert prerequisite_met(settings, "acme", research) is True


def test_stage_blocked_until_prerequisite_exists(settings):
    brand = PIPELINE_BY_KEY["brand-strategy"]
    # research.md does not exist yet -> blocked
    assert prerequisite_met(settings, "acme", brand) is False
    # create the prerequisite deliverable -> unblocked
    (settings.campaigns_dir / "acme" / "research.md").write_text("findings", encoding="utf-8")
    assert prerequisite_met(settings, "acme", brand) is True


def test_deliverable_path(settings):
    research = PIPELINE_BY_KEY["research"]
    p = deliverable_path(settings, "acme", research)
    assert p == settings.campaigns_dir / "acme" / "research.md"

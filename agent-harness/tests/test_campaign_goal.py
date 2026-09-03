"""Tests for the campaign-goal domain: rendering, parsing, slugs and segments.

The renderer's contract is that what it writes passes the same gate that reads a
hand-authored goal, so these tests assert against ``check_gate`` and the real
``templates/campaign-goal.md`` rather than against a hand-written expectation of
the markdown.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import TENANT, filled_dna_answers
from marketing_os.campaign import (
    Budget,
    CampaignGoal,
    KpiTiers,
    Timeframe,
    allocate_slug,
    audience_segments,
    missing_goal_fields,
    parse_campaign_goal,
    render_campaign_goal,
)
from marketing_os.config import Settings
from marketing_os.governance import check_gate
from marketing_os.questionnaire import SEED_QUESTIONNAIRE, render_brand_dna


def _goal() -> CampaignGoal:
    """Build a complete campaign goal.

    Returns:
        A goal with every Required field filled.
    """
    return CampaignGoal(
        name="Spring Refill Push",
        objective="120 refill subscriptions in 8 weeks",
        timeframe=Timeframe(start_date="2026-09-01", end_date="2026-10-27"),
        budget=Budget(amount=4000, currency="SGD"),
        audience_segment="Weekday regulars",
        kpis=KpiTiers(
            business="120 refill subscriptions",
            marketing="2.5% landing-page conversion",
            creative="30% hook rate on launch video",
        ),
    )


def test_rendered_goal_passes_the_gate(settings: Settings, repo: Path) -> None:
    from marketing_os.adapters.documents import FilesystemDocumentStore

    store = FilesystemDocumentStore(repo)
    store.write(TENANT, "campaigns/spring/goal.md", render_campaign_goal(_goal()))

    report = check_gate(settings, TENANT, "spring", store=store, questionnaire=SEED_QUESTIONNAIRE)

    assert report.goal_issues == []


def test_rendered_goal_round_trips_through_the_parser() -> None:
    goal = _goal()

    assert parse_campaign_goal(render_campaign_goal(goal)) == goal


def test_rendered_goal_titles_the_document_with_the_campaign_name() -> None:
    assert render_campaign_goal(_goal()).startswith("# Campaign Goal — Spring Refill Push")


def test_rendered_goal_never_names_the_business() -> None:
    """ADR-0013: a tenant is one business, so the goal carries no business identity."""
    assert "Customer:" not in render_campaign_goal(_goal())


def test_optional_offer_is_rendered_when_given() -> None:
    goal = _goal().model_copy(update={"offer": "First month half price"})

    assert "**Offer / promotion:** First month half price" in render_campaign_goal(goal)


def test_optional_offer_is_omitted_when_blank() -> None:
    assert "Offer / promotion" not in render_campaign_goal(_goal())


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        ("name", "name"),
        ("objective", "objective"),
        ("audience_segment", "audience_segment"),
    ],
)
def test_missing_top_level_field_is_named_specifically(field: str, expected: str) -> None:
    goal = _goal().model_copy(update={field: "  "})

    assert missing_goal_fields(goal) == [expected]


@pytest.mark.parametrize("tier", ["business", "marketing", "creative"])
def test_each_missing_kpi_tier_is_named_specifically(tier: str) -> None:
    goal = _goal()
    goal = goal.model_copy(update={"kpis": goal.kpis.model_copy(update={tier: ""})})

    assert missing_goal_fields(goal) == [f"kpis.{tier}"]


def test_a_complete_goal_reports_nothing_missing() -> None:
    assert missing_goal_fields(_goal()) == []


def test_every_missing_field_is_reported_not_only_the_first() -> None:
    goal = _goal().model_copy(update={"name": "", "objective": ""})

    assert missing_goal_fields(goal) == ["name", "objective"]


def test_allocate_slug_kebab_cases_the_name() -> None:
    assert allocate_slug("Spring Refill Push", taken=[]) == "spring-refill-push"


def test_allocate_slug_suffixes_on_collision() -> None:
    assert allocate_slug("Spring", taken=["spring"]) == "spring-2"
    assert allocate_slug("Spring", taken=["spring", "spring-2"]) == "spring-3"


def test_allocate_slug_falls_back_when_the_name_has_no_usable_characters() -> None:
    assert allocate_slug("!!!", taken=[]) == "campaign"


def test_audience_segments_come_from_the_brand_dna() -> None:
    dna = render_brand_dna(
        SEED_QUESTIONNAIRE, filled_dna_answers(), business_name="Acme Climbing Gym"
    )

    assert audience_segments(dna) == ["Urban 22-35 beginners curious about climbing"]


def test_audience_segments_splits_a_multi_line_answer_and_drops_the_detail() -> None:
    dna = "\n".join(
        [
            "# Brand DNA — Acme",
            "",
            "- **Primary segment(s):**",
            "  - Weekday regulars — buy a drink every morning",
            "  - Weekend families — larger orders, price sensitive",
        ]
    )

    assert audience_segments(dna) == ["Weekday regulars", "Weekend families"]


def test_audience_segments_is_empty_when_the_dna_names_none() -> None:
    assert audience_segments("# Brand DNA — Acme\n") == []

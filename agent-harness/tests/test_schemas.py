"""Schemas: the decision envelope and per-stage strict deliverables validate."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from marketing_os.schemas import (
    STAGE_SCHEMAS,
    DecisionEnvelope,
    EvalReport,
    ResearchFindings,
    RiskLevel,
    StrategyDoc,
)


def test_decision_envelope_minimal_and_defaults():
    env = DecisionEnvelope(
        thought_summary="need evidence",
        next_action="web_search",
        reason="strategy needs current data",
        expected_observation="recent sources",
    )
    assert env.risk_level == RiskLevel.low
    assert env.requires_approval is False
    assert env.tool_args == {}


def test_decision_envelope_parses_json_like_user_example():
    raw = (
        '{"thought_summary":"Need customer pain evidence before strategy.",'
        '"next_action":"web_search","tool_name":"open_page",'
        '"tool_args":{"url":"https://example.com"},'
        '"reason":"strategy requires market evidence",'
        '"expected_observation":"data about SME constraints",'
        '"risk_level":"low","requires_approval":false}'
    )
    env = DecisionEnvelope.model_validate_json(raw)
    assert env.tool_name == "open_page"
    assert env.tool_args["url"].startswith("https://")


def test_stage_schemas_cover_all_pipeline_stages():
    assert set(STAGE_SCHEMAS) == {
        "intake",
        "research",
        "strategy",
        "campaign_strategy",
        "creative",
        "asset_prompts",
        "media",
        "evaluator",
        "execution",
        "performance",
    }


def test_strategy_and_eval_schemas_roundtrip():
    s = StrategyDoc(
        positioning="p", core_message="m", value_proposition="v",
        campaign_hypothesis="h", why="because evidence",
    )
    assert s.supporting_points == []
    e = EvalReport(
        passed=False, strategy_quality="weak", brand_fit="ok",
        feasibility="ok", evidence_grounding="thin", issues=["no competitor data"],
    )
    assert e.passed is False and e.issues


def test_research_findings_requires_known_fields():
    with pytest.raises(ValidationError):
        ResearchFindings(customer="not-a-list")  # type: ignore[arg-type]

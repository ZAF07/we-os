"""Pydantic schemas for the harness.

Two families:

1. ``DecisionEnvelope`` — the per-step reasoning/control trace every worker agent
   is asked to think in. It is captured by callbacks into memory and logs and its
   ``risk_level`` / ``requires_approval`` fields feed the human-check gate.
2. One strict deliverable schema per pipeline stage. The stage's *formatter*
   sub-agent runs with ``output_schema`` set to one of these, so each stage emits
   validated, typed JSON the next stage (and the API) can rely on.

Schemas are deliberately shallow (ADK ``output_schema`` works most reliably with
flat, JSON-Schema-friendly models) and avoid features ADK strips (no numeric
bounds, no recursion).
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ── Per-step decision envelope ────────────────────────────────────────────────
class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class DecisionEnvelope(BaseModel):
    """A single agent step's reasoning + intended next action.

    Captured every step (via callbacks) as an audit trail and to drive the
    human-check gate. Mirrors the schema the user specified.
    """

    thought_summary: str = Field(description="Why this step is needed, in one or two sentences.")
    next_action: str = Field(description="What the agent will do next (tool call, write, finish).")
    tool_name: Optional[str] = Field(default=None, description="Tool to invoke, if any.")
    tool_args: dict = Field(default_factory=dict, description="Arguments for the tool call.")
    reason: str = Field(description="How this action advances the overall and current goal.")
    expected_observation: str = Field(description="What result the agent expects back.")
    risk_level: RiskLevel = Field(default=RiskLevel.low, description="Blast radius of the action.")
    requires_approval: bool = Field(
        default=False, description="Whether a human must approve before proceeding."
    )


# ── Shared sub-models ─────────────────────────────────────────────────────────
class Evidence(BaseModel):
    """A single sourced finding."""

    claim: str = Field(description="The finding, stated plainly.")
    source: str = Field(description="Where it came from (URL, framework, or DNA reference).")


class KpiTier(BaseModel):
    """The three mandatory KPI tiers for a campaign."""

    business: str = Field(description="Business KPI target (revenue/leads/bookings/sales/retention).")
    marketing: str = Field(description="Marketing KPI target (CTR/CPC/CPM/conversion-rate).")
    creative: str = Field(description="Creative KPI target (hook rate/watch time/engagement).")


# ── Per-stage deliverable schemas ─────────────────────────────────────────────
class IntakeBrief(BaseModel):
    """Stage 1 — structured extraction of the campaign request."""

    business: str
    offer: str
    target_segment: str
    primary_objective: str = Field(description="The single measurable business outcome.")
    constraints: List[str] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)


class ResearchFindings(BaseModel):
    """Stage 2 — evidence only (no strategy)."""

    customer: List[Evidence] = Field(default_factory=list)
    competitor: List[Evidence] = Field(default_factory=list)
    market: List[Evidence] = Field(default_factory=list)
    trends: List[Evidence] = Field(default_factory=list)
    segments: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list, description="Honestly-flagged unknowns.")


class StrategyDoc(BaseModel):
    """Stage 3 — positioning + campaign hypothesis."""

    positioning: str
    core_message: str
    supporting_points: List[str] = Field(default_factory=list)
    value_proposition: str
    campaign_hypothesis: str = Field(description="The testable bet this campaign makes.")
    why: str = Field(description="How the strategy ties to the business objective and evidence.")


class CreativeConcept(BaseModel):
    """One creative concept."""

    name: str
    big_idea: str
    formats: List[str] = Field(default_factory=list, description="Asset formats this concept needs.")
    ties_to_message: str = Field(description="Which strategy message this expresses.")


class CreativeConcepts(BaseModel):
    """Stage 4 — creative concepts (briefs, not finished assets)."""

    concepts: List[CreativeConcept] = Field(default_factory=list)
    theme: str


class MediaPlan(BaseModel):
    """Stage 5 — channels + test structure + KPIs + budget."""

    channels: List[str] = Field(default_factory=list)
    channel_rationale: str
    test_structure: str = Field(description="How variants/audiences will be tested.")
    budget_allocation: str
    kpis: KpiTier


class CampaignStrategyDoc(BaseModel):
    """Campaign strategy — the Marketing Director's approach (owns campaign-strategy.md)."""

    approach: str = Field(description="How the campaign will achieve the business objective.")
    channels_at_a_glance: List[str] = Field(
        default_factory=list, description="Shortlist of channels, each with a one-line rationale."
    )
    budget_allocation: str
    kpis: KpiTier
    why: str = Field(description="How the approach ties to the business objective and strategy.")


class AssetPrompt(BaseModel):
    """A single generation prompt traced to a brief requirement."""

    brief_requirement: str = Field(description="The creative-brief requirement this fulfills.")
    medium: str = Field(description="image | video | ad | landing_page")
    prompt: str = Field(description="The generation prompt, strictly following the brief.")


class AssetPrompts(BaseModel):
    """Asset prompts — generation prompts derived strictly from the creative brief."""

    prompts: List[AssetPrompt] = Field(default_factory=list)


class EvalReport(BaseModel):
    """The Evaluator's verdict gating human approval."""

    passed: bool
    strategy_quality: str
    brand_fit: str
    feasibility: str
    evidence_grounding: str
    issues: List[str] = Field(default_factory=list, description="Remaining problems if not passed.")


class ExecutionDrafts(BaseModel):
    """Stage 8 — concrete draft assets."""

    assets: List[str] = Field(
        default_factory=list, description="Draft posts/ad copy/landing-page sections."
    )
    notes: str = Field(default="", description="Production notes for the operator.")


class PerformancePlan(BaseModel):
    """Stage 9 — monitoring + iteration recommendations."""

    metrics_to_watch: List[str] = Field(default_factory=list)
    iteration_recommendations: List[str] = Field(default_factory=list)
    why: str


# Map stage key -> its strict deliverable schema (used by the formatter builder).
# The six .claude pipeline stages (research → … → performance-plan/media) run in
# order inside the refine loop; intake/execution/performance wrap it.
STAGE_SCHEMAS: dict[str, type[BaseModel]] = {
    "intake": IntakeBrief,
    "research": ResearchFindings,
    "strategy": StrategyDoc,  # brand strategy -> brand-strategy.md
    "campaign_strategy": CampaignStrategyDoc,  # -> campaign-strategy.md
    "creative": CreativeConcepts,  # creative brief -> creative-brief.md
    "asset_prompts": AssetPrompts,  # -> asset-prompts.md
    "media": MediaPlan,  # performance plan -> performance-plan.md
    "evaluator": EvalReport,
    "execution": ExecutionDrafts,
    "performance": PerformancePlan,
}

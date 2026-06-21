"""The mandatory decision pipeline.

Encodes the stage order, who owns each stage, the deliverable each writes, and
the prerequisite deliverable that gates it. A stage cannot start until its
prerequisite file exists on disk — the same "deliverable-exists is the gate"
rule the orchestrator skill enforces. Never reordered, never skipped.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..config import Settings

# Sentinel for stages the Marketing Director (orchestrator) owns directly,
# rather than delegating to a specialist subagent.
DIRECTOR = "marketing-director"


@dataclass(frozen=True)
class Stage:
    key: str  # short stage id used in CLI/API
    agent: str  # specialist agent name, or DIRECTOR for orchestrator-owned
    deliverable: str  # filename written under campaigns/<slug>/
    prerequisite: Optional[str]  # deliverable filename required first (None = gated by Stage 0 only)
    task: str  # brief handed to the agent (formatted with paths/context)


# Order is mandatory and mirrors .claude/rules/decision-hierarchy.md +
# .claude/skills/new-campaign. Brief templates reference inputs by repo path so
# the agent reads upstream deliverables with its own tools.
PIPELINE: list[Stage] = [
    Stage(
        key="research",
        agent="market-research",
        deliverable="research.md",
        prerequisite=None,
        task=(
            "Conduct market research for this campaign. Read the campaign goal at "
            "{goal_path} and the Customer DNA at {dna_path}. Produce customer, "
            "competitor, market, trend, and audience-segmentation findings — findings "
            "only, no strategy. Cite the framework behind each finding and flag gaps "
            "honestly. Save the result to {deliverable_path}."
        ),
    ),
    Stage(
        key="brand-strategy",
        agent="brand-strategy",
        deliverable="brand-strategy.md",
        prerequisite="research.md",
        task=(
            "Develop brand strategy. Read the research findings at {prereq_path}, the "
            "goal at {goal_path}, and the Customer DNA at {dna_path}. Produce "
            "positioning, messaging, brand personality/voice, and value proposition — "
            "each explained with the 'why', grounded in a research finding. Save to "
            "{deliverable_path}."
        ),
    ),
    Stage(
        key="campaign-strategy",
        agent=DIRECTOR,
        deliverable="campaign-strategy.md",
        prerequisite="brand-strategy.md",
        task=(
            "As the Marketing Director, set the campaign strategy. Read the approved "
            "brand strategy at {prereq_path}, the goal at {goal_path}, and the DNA at "
            "{dna_path}. Decide the campaign approach, channels-at-a-glance, budget "
            "allocation, and the three KPI tiers (Business / Marketing / Creative). "
            "Tie every choice to the business objective. Save to {deliverable_path}."
        ),
    ),
    Stage(
        key="creative-brief",
        agent="creative-director",
        deliverable="creative-brief.md",
        prerequisite="campaign-strategy.md",
        task=(
            "Produce the creative brief. Read the approved strategy at {prereq_path}, "
            "the brand strategy, the goal at {goal_path}, and the DNA at {dna_path}. "
            "Deliver creative concepts, campaign themes, content directions, and clear "
            "asset requirements (channel + spec) — briefs only, no generation prompts. "
            "Tie every concept to the business objective. Save to {deliverable_path}."
        ),
    ),
    Stage(
        key="asset-prompts",
        agent="creative-asset-prompt",
        deliverable="asset-prompts.md",
        prerequisite="creative-brief.md",
        task=(
            "Convert the approved creative brief at {prereq_path} into generation "
            "prompts for images, videos, ads, and landing pages. Each prompt must trace "
            "to a specific brief requirement and strictly follow it — invent no new "
            "strategy. Ground in the DNA at {dna_path}. Save to {deliverable_path}."
        ),
    ),
    Stage(
        key="performance-plan",
        agent="performance-marketing",
        deliverable="performance-plan.md",
        prerequisite="asset-prompts.md",
        task=(
            "Produce the performance plan. Read the campaign strategy, creative brief at "
            "{prereq_path}, the goal at {goal_path}, and the DNA at {dna_path}. Specify "
            "channel selection (with rationale), campaign setup, the KPI plan across all "
            "three tiers, and budget allocation. Define success metrics before "
            "recommending spend; tie every recommendation to the business KPI. Save to "
            "{deliverable_path}."
        ),
    ),
]

PIPELINE_BY_KEY: dict[str, Stage] = {s.key: s for s in PIPELINE}


def campaign_dir(settings: Settings, slug: str) -> Path:
    return settings.campaigns_dir / slug


def deliverable_path(settings: Settings, slug: str, stage: Stage) -> Path:
    return campaign_dir(settings, slug) / stage.deliverable


def prerequisite_met(settings: Settings, slug: str, stage: Stage) -> bool:
    """True if the stage may begin (its prerequisite deliverable exists)."""
    if stage.prerequisite is None:
        return True
    return (campaign_dir(settings, slug) / stage.prerequisite).is_file()

"""The mandatory decision pipeline.

Encodes the stage order, who owns each stage, the deliverable each writes, and
the prerequisite deliverable that gates it. A stage cannot start until its
prerequisite file exists on disk — the same "deliverable-exists is the gate"
rule the orchestrator skill enforces. Never reordered, never skipped.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from marketing_os.config import Settings

# Sentinel for stages the Marketing Director (orchestrator) owns directly,
# rather than delegating to a specialist subagent.
DIRECTOR = "marketing-director"


@dataclass(frozen=True)
class Stage:
    """One mandatory pipeline stage.

    Attributes:
        key: The short stage id used in the CLI and API.
        agent: The specialist agent name, or ``DIRECTOR`` for the Director-owned stage.
        deliverable: The filename written under ``campaigns/<slug>/``.
        prerequisite: The deliverable filename required first, or ``None`` when the
            stage is gated only by Stage 0.
        task: The brief handed to the agent, formatted with paths and context.
    """

    key: str
    agent: str
    deliverable: str
    prerequisite: str | None
    task: str


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
    """Return the directory holding a campaign's deliverables.

    Args:
        settings: The harness settings.
        slug: The campaign slug.

    Returns:
        The ``campaigns/<slug>/`` directory path.
    """
    return settings.campaigns_dir / slug


def deliverable_path(settings: Settings, slug: str, stage: Stage) -> Path:
    """Return the path a stage writes its deliverable to.

    Args:
        settings: The harness settings.
        slug: The campaign slug.
        stage: The pipeline stage.

    Returns:
        The absolute path of the stage's deliverable file.
    """
    return campaign_dir(settings, slug) / stage.deliverable


def prerequisite_met(settings: Settings, slug: str, stage: Stage) -> bool:
    """True if the stage may begin (its prerequisite deliverable exists)."""
    if stage.prerequisite is None:
        return True
    return (campaign_dir(settings, slug) / stage.prerequisite).is_file()

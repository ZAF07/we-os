"""The mandatory decision pipeline.

Encodes the stage order, who owns each stage, the deliverable each writes, and
the prerequisite deliverable that gates it. A stage cannot start until its
prerequisite deliverable exists in the document store — the same
"deliverable-exists is the gate" rule the orchestrator skill enforces. Never
reordered, never skipped.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from marketing_os.config import Settings
from marketing_os.ports import DocumentStore

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
            "{goal_path} and the Brand DNA at {dna_path}. Produce customer, "
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
            "goal at {goal_path}, and the Brand DNA at {dna_path}. Produce "
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
            "{dna_path}. Decide the campaign approach, a rough channel direction, and "
            "the three KPI tiers (Business / Marketing / Creative) — the performance "
            "plan will make the channel mix and spend allocation concrete. Tie every "
            "choice to the business objective. Save to {deliverable_path}."
        ),
    ),
    Stage(
        key="performance-plan",
        agent="performance-marketing",
        deliverable="performance-plan.md",
        prerequisite="campaign-strategy.md",
        task=(
            "Produce the performance plan. Read the approved campaign strategy at "
            "{prereq_path}, the goal at {goal_path}, and the DNA at {dna_path}. Decide "
            "the concrete channel mix (with rationale), the per-channel spend allocation "
            "of the campaign budget, KPI targets across all three tiers, and the "
            "placement/format requirements creative must satisfy on each channel "
            "(placement, aspect ratio, dimensions/length, copy limits). Define success "
            "metrics before recommending spend; tie every recommendation to the "
            "business KPI. Save to {deliverable_path}."
        ),
    ),
    Stage(
        key="creative-brief",
        agent="creative-director",
        deliverable="creative-brief.md",
        prerequisite="performance-plan.md",
        task=(
            "Produce the creative brief. Read the approved performance plan at "
            "{prereq_path}, the campaign strategy, the brand strategy, the goal at "
            "{goal_path}, and the DNA at {dna_path}. Brief against the placements the "
            "performance plan chose: deliver creative concepts, campaign themes, content "
            "directions, and asset requirements that name each placement and honour its "
            "format spec — briefs only, no generation prompts. Tie every concept to the "
            "business objective. Save to {deliverable_path}."
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
            "to a specific brief requirement and strictly follow it — including the "
            "placement and format spec the brief names — invent no new strategy. Ground "
            "in the DNA at {dna_path}. Save to {deliverable_path}."
        ),
    ),
]

PIPELINE_BY_KEY: dict[str, Stage] = {s.key: s for s in PIPELINE}


def campaign_dir(settings: Settings, slug: str) -> Path:
    """Return the filesystem directory holding a campaign's deliverables.

    Describes the repository layout the filesystem adapter serves; store-backed
    code should address documents via :func:`stage_document` instead.

    Args:
        settings: The harness settings.
        slug: The campaign slug.

    Returns:
        The ``campaigns/<slug>/`` directory path.
    """
    return settings.campaigns_dir / slug


def deliverable_path(settings: Settings, slug: str, stage: Stage) -> Path:
    """Return the filesystem path a stage's deliverable lives at.

    Describes the repository layout the filesystem adapter serves; store-backed
    code should address documents via :func:`stage_document` instead.

    Args:
        settings: The harness settings.
        slug: The campaign slug.
        stage: The pipeline stage.

    Returns:
        The absolute path of the stage's deliverable file.
    """
    return campaign_dir(settings, slug) / stage.deliverable


def stage_document(slug: str, stage: Stage) -> str:
    """Return the tenant-relative document path of a stage's deliverable.

    Args:
        slug: The campaign slug.
        stage: The pipeline stage.

    Returns:
        The ``campaigns/<slug>/<deliverable>`` document path.
    """
    return f"campaigns/{slug}/{stage.deliverable}"


def prerequisite_met(store: DocumentStore, tenant: str, slug: str, stage: Stage) -> bool:
    """True if the stage may begin (its prerequisite deliverable exists).

    Args:
        store: The document store deliverables resolve through.
        tenant: The tenant the campaign belongs to.
        slug: The campaign slug.
        stage: The pipeline stage to check.

    Returns:
        Whether the prerequisite deliverable exists (always ``True`` for the
        first stage, which is gated only by Stage 0).
    """
    if stage.prerequisite is None:
        return True
    return store.exists(tenant, f"campaigns/{slug}/{stage.prerequisite}")

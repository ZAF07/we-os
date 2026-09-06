"""The mandatory decision pipeline.

Encodes the stage order, who owns each stage, the deliverable each writes, the
prerequisite deliverable that gates it, and whether a person must approve it. A
stage cannot start until its prerequisite deliverable exists in the document
store — the same "deliverable-exists is the gate" rule the orchestrator skill
enforces. Never reordered, never skipped.

The **approval policy** is data rather than code (ADR-0015): ``auto`` advances
on a passing QA verdict, ``human`` halts at an Approval Gate until a person says
yes. Tightening or loosening the gates is therefore a configuration change
(:func:`apply_approval_policies`), not a rewrite of the graph.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from marketing_os.ports import DocumentStore

# Sentinel for stages the Marketing Director (orchestrator) owns directly,
# rather than delegating to a specialist subagent.
DIRECTOR = "marketing-director"

# The two approval policies a stage can carry.
AUTO = "auto"
HUMAN = "human"


@dataclass(frozen=True)
class Stage:
    """One mandatory pipeline stage.

    Attributes:
        key: The short stage id used in the API.
        agent: The specialist agent name, or ``DIRECTOR`` for the Director-owned stage.
        deliverable: The filename written under ``campaigns/<slug>/``.
        prerequisite: The deliverable filename required first, or ``None`` when the
            stage is gated only by Stage 0.
        task: The brief handed to the agent, formatted with paths and context.
        approval_policy: :data:`AUTO` to advance on a passing QA verdict, or
            :data:`HUMAN` to halt at an Approval Gate until a person approves.
        phase: The operator-facing grouping the stage belongs to. A phase may
            cover more than one stage; phases are presentation and stages stay
            canonical, so the engine never adopts UI vocabulary (ADR-0017).
    """

    key: str
    agent: str
    deliverable: str
    prerequisite: str | None
    task: str
    approval_policy: str = HUMAN
    phase: str = ""


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
        approval_policy=AUTO,
        phase="Research",
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
        phase="Strategy",
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
        phase="Strategy",
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
        phase="Plan",
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
        phase="Produce",
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
        phase="Produce",
    ),
]

PIPELINE_BY_KEY: dict[str, Stage] = {s.key: s for s in PIPELINE}


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


def apply_approval_policies(stages: list[Stage], human_stages: list[str] | None) -> list[Stage]:
    """Return the pipeline with its approval policies set from configuration.

    The policy is data, so an operator tunes the friction without a rewrite
    (ADR-0015). ``human_stages`` names every stage that halts at an Approval
    Gate; each other stage advances on a passing QA verdict. ``None`` means no
    configuration was supplied, so the shipped defaults stand.

    Args:
        stages: The pipeline stages to re-policy, in order.
        human_stages: The stage keys requiring human approval, or ``None`` to
            keep each stage's shipped policy.

    Returns:
        The stages in the same order, each carrying its configured policy.
    """
    if human_stages is None:
        return list(stages)
    required = set(human_stages)
    return [
        replace(stage, approval_policy=HUMAN if stage.key in required else AUTO) for stage in stages
    ]

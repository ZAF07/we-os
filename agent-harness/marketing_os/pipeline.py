"""Assemble the coordinator: the 9-stage marketing pipeline as an ADK agent graph.

Shape (a `SequentialAgent` coordinator)::

    intake → research
           → refine_loop( strategy → creative → media → evaluator → eval_gate )
           → [approval_gate]            (only if enabled in agents.yaml)
           → execution → performance

The refine loop is a `LoopAgent`: each pass runs strategy→creative→media, the
Evaluator judges the package, and the `EscalationGate` ends the loop the moment
the verdict passes (or after `max_iterations`). This is the "check its own work
against the goal and iterate" behavior, with the human approval gate downstream.
"""

from __future__ import annotations

from google.adk.agents import LoopAgent, SequentialAgent

from .agents import (
    BuildContext,
    EscalationGate,
    build_approval_stage,
    build_evaluator,
    build_stage,
    make_skip_if_done,
)
from .runstate import eval_passed

#: The stage keys whose strict deliverables we collect from session state at the
#: end, in execution order. The six middle keys are the .claude pipeline that runs
#: inside the refine loop (research → brand-strategy → campaign-strategy →
#: creative-brief → asset-prompts → performance-plan).
DELIVERABLE_KEYS = [
    "intake",
    "research",
    "strategy",
    "campaign_strategy",
    "creative",
    "asset_prompts",
    "media",
    "eval",
    "execution",
    "performance",
]


def build_coordinator(ctx: BuildContext) -> SequentialAgent:
    """Build the full coordinator agent for one campaign run.

    Args:
        ctx: Shared build dependencies (model, governance, registry, tools, sink).

    Returns:
        A `SequentialAgent` ready to hand to an ADK `Runner`.
    """
    # The refine loop runs the six .claude pipeline stages in their canonical
    # order, then the Evaluator judges the whole package and the gate ends the loop
    # once it passes. Stages inside the loop carry NO skip guard — they re-run each
    # iteration so the Evaluator can drive revision across the full pipeline.
    refine_loop = LoopAgent(
        name="refine_loop",
        max_iterations=ctx.settings.max_eval_iterations,
        sub_agents=[
            build_stage(ctx, "research"),  # research.md
            build_stage(ctx, "strategy"),  # brand-strategy.md
            build_stage(ctx, "campaign_strategy"),  # campaign-strategy.md
            build_stage(ctx, "creative"),  # creative-brief.md
            build_stage(ctx, "asset_prompts"),  # asset-prompts.md
            build_stage(ctx, "media"),  # performance-plan.md
            build_evaluator(ctx),
            EscalationGate(name="eval_gate"),
        ],
        # On resume, skip the whole refine loop only if a PASSING verdict already
        # exists — a present-but-failed eval means keep iterating.
        before_agent_callback=make_skip_if_done("refine_loop", eval_passed),
    )

    # Intake precedes the loop; execution/performance follow it. These linear
    # stages skip on resume when their deliverable is already present.
    sub_agents = [
        build_stage(ctx, "intake", skip_if_present="intake"),
        refine_loop,
    ]
    approval = build_approval_stage(ctx)
    if approval is not None:
        sub_agents.append(approval)
    sub_agents += [
        build_stage(ctx, "execution", skip_if_present="execution"),
        build_stage(ctx, "performance", skip_if_present="performance"),
    ]

    return SequentialAgent(name="marketing_coordinator", sub_agents=sub_agents)

import type { CampaignStage } from "@/lib/engine";
import type { Status } from "@/lib/status";

/**
 * Projects the engine's stages onto what the Workspace renders.
 *
 * The engine speaks stages and lifecycle; the interface speaks Phases and
 * status labels. That translation lives here, on the frontend side of the line
 * ADR-0017 draws, so the engine never adopts UI vocabulary and the interface
 * never shows a raw stage key.
 */

/** The deliverable filename each engine stage writes. */
const STAGE_DELIVERABLES: Record<string, string> = {
  research: "research.md",
  "brand-strategy": "brand-strategy.md",
  "campaign-strategy": "campaign-strategy.md",
  "performance-plan": "performance-plan.md",
  "creative-brief": "creative-brief.md",
  "asset-prompts": "asset-prompts.md",
};

/** What each engine stage is called when a person reads it. */
const STAGE_TITLES: Record<string, string> = {
  research: "Research findings",
  "brand-strategy": "Brand strategy",
  "campaign-strategy": "Campaign strategy",
  "performance-plan": "Performance plan",
  "creative-brief": "Creative brief",
  "asset-prompts": "Asset prompts",
};

/** The engine's per-stage states in the operator's status vocabulary. */
const STAGE_STATUSES: Record<string, Status> = {
  pending: "Not started",
  completed: "Approved",
  awaiting_approval: "Ready for review",
  stale: "Stale",
};

export interface PhaseView {
  name: string;
  stages: CampaignStage[];
  status: Status;
}

/**
 * Names the deliverable filename a stage writes.
 *
 * Args:
 *   stageKey: The engine stage key.
 *
 * Returns:
 *   The filename the deliverable endpoints address the stage by.
 */
export function deliverableName(stageKey: string): string {
  return STAGE_DELIVERABLES[stageKey] ?? `${stageKey}.md`;
}

/**
 * Names a stage as the interface shows it.
 *
 * Args:
 *   stageKey: The engine stage key.
 *
 * Returns:
 *   The stage's operator-facing title, never the raw key.
 */
export function stageTitle(stageKey: string): string {
  return STAGE_TITLES[stageKey] ?? stageKey;
}

/**
 * Converts an engine stage state into the operator's status label.
 *
 * Args:
 *   state: The engine's stage state.
 *
 * Returns:
 *   The status the interface shows, defaulting to Not started for a state it
 *   does not recognise rather than rendering a raw engine string.
 */
export function stageStatus(state: string): Status {
  return STAGE_STATUSES[state] ?? "Not started";
}

/**
 * Groups the engine's stages into the operator Phases the stepper renders.
 *
 * A Phase covers one or more stages, so its status is the least-advanced thing
 * a person needs to know about it: a Phase holding a stage at a gate reads
 * Ready for review, one holding stale work reads Stale, and it only reads
 * Approved once every stage under it has completed.
 *
 * Args:
 *   stages: The campaign's stages in pipeline order, as the engine reports them.
 *
 * Returns:
 *   One entry per Phase the campaign has stages for, in pipeline order.
 */
export function toPhases(stages: CampaignStage[]): PhaseView[] {
  const phases: PhaseView[] = [];
  for (const stage of stages) {
    const existing = phases.find((phase) => phase.name === stage.phase);
    if (existing) {
      existing.stages.push(stage);
    } else {
      phases.push({
        name: stage.phase,
        stages: [stage],
        status: "Not started",
      });
    }
  }
  return phases.map((phase) => ({
    ...phase,
    status: phaseStatus(phase.stages),
  }));
}

/**
 * Reduces a Phase's stages to the one status that describes the Phase.
 *
 * Args:
 *   stages: The stages the Phase groups.
 *
 * Returns:
 *   The Phase's status.
 */
function phaseStatus(stages: CampaignStage[]): Status {
  if (stages.some((stage) => stage.state === "awaiting_approval")) {
    return "Ready for review";
  }
  if (stages.some((stage) => stage.stale)) return "Stale";
  if (stages.every((stage) => stage.state === "completed")) return "Approved";
  if (stages.some((stage) => stage.latest_version !== null)) {
    return "In progress";
  }
  return "Not started";
}

/**
 * Finds the stage a campaign is halted at, waiting for a person to decide.
 *
 * Args:
 *   stages: The campaign's stages.
 *
 * Returns:
 *   The waiting stage, or null when nothing is at a gate.
 */
export function stageAwaitingApproval(
  stages: CampaignStage[],
): CampaignStage | null {
  return stages.find((stage) => stage.state === "awaiting_approval") ?? null;
}

/**
 * Chooses the stage the Workspace opens on.
 *
 * A person arriving at a campaign wants the decision in front of them, so a
 * stage at a gate wins; otherwise the newest thing produced, and failing that
 * the first stage of the pipeline.
 *
 * Args:
 *   stages: The campaign's stages in pipeline order.
 *
 * Returns:
 *   The stage key to select, or null when the campaign has no stages.
 */
export function defaultStageKey(stages: CampaignStage[]): string | null {
  const waiting = stageAwaitingApproval(stages);
  if (waiting) return waiting.key;
  const produced = stages.filter((stage) => stage.latest_version !== null);
  if (produced.length > 0) return produced[produced.length - 1].key;
  return stages[0]?.key ?? null;
}

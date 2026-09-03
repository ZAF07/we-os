import type { CampaignSummary } from "@/lib/engine";
import type { Status } from "@/lib/status";

/**
 * The engine's lifecycle statuses in the operator's vocabulary.
 *
 * The engine speaks lifecycle (`draft` → `running` → … → `archived`) and never
 * adopts UI wording; the mapping to what the interface shows lives here, on the
 * frontend side of that line (ADR-0017).
 */
const STATUS_LABELS: Record<string, Status> = {
  draft: "Draft",
  running: "In progress",
  awaiting_approval: "Ready for review",
  approved: "Approved",
  published: "Published",
  measuring: "In progress",
  archived: "Archived",
};

/** The operator Phase each engine stage belongs to, as the engine reports it. */
const STAGE_PHASES: Record<string, string> = {
  research: "Research",
  "brand-strategy": "Strategy",
  "campaign-strategy": "Strategy",
  "performance-plan": "Plan",
  "creative-brief": "Produce",
  "asset-prompts": "Produce",
};

export interface CampaignRowView {
  slug: string;
  name: string;
  objective: string;
  stage: string;
  stageNum: string;
  status: Status;
  next: string;
}

/**
 * Converts an engine lifecycle status into the operator's status label.
 *
 * Args:
 *   status: The engine's lifecycle status.
 *
 * Returns:
 *   The status the interface shows, defaulting to Draft for one it does not
 *   recognise rather than rendering a raw engine string.
 */
export function statusLabel(status: string): Status {
  return STATUS_LABELS[status] ?? "Draft";
}

/**
 * Names the Phase a stage belongs to, for the stage column.
 *
 * Args:
 *   stageKey: The engine stage key, or null when no stage is current.
 *
 * Returns:
 *   The operator Phase, or `Done` when every stage has completed.
 */
export function phaseLabel(stageKey: string | null): string {
  if (stageKey === null) return "Done";
  return STAGE_PHASES[stageKey] ?? stageKey;
}

/**
 * Projects a campaign summary onto a row of the portfolio table.
 *
 * Args:
 *   campaign: The summary the engine reported.
 *
 * Returns:
 *   The table row.
 */
export function toCampaignRow(campaign: CampaignSummary): CampaignRowView {
  const { completed, total, current_stage_key } = campaign.stage_progress;
  return {
    slug: campaign.id,
    name: campaign.name,
    objective: campaign.objective,
    stage: phaseLabel(current_stage_key),
    stageNum: `${completed}/${total}`,
    status: statusLabel(campaign.status),
    next: campaign.blocked_reason ?? "—",
  };
}

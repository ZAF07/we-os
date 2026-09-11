import type { CampaignSummary } from "@/lib/engine";
import type { Status } from "@/lib/status";
import { stageTitle } from "@/lib/workspace";

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
  awaiting_clarification: "Needs input",
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
 * Says what is holding a campaign up, naming the stage that needs a person.
 *
 * The engine reports only which stage is holding and why the campaign is
 * halted; the sentence is put together here so Home and the Campaigns table
 * say the same thing (ADR-0017).
 *
 * Args:
 *   campaign: The summary the engine reported.
 *
 * Returns:
 *   The reason, or null when nothing is blocking the campaign.
 */
export function blockedReason(campaign: CampaignSummary): string | null {
  const stageKey = campaign.blocked_stage_key;
  const stage = stageKey === null ? "A stage" : stageTitle(stageKey);
  if (campaign.status === "awaiting_approval") {
    return `${stage} is waiting for your approval.`;
  }
  if (campaign.status === "awaiting_clarification") {
    return `${stage} has a question for you.`;
  }
  if (stageKey === null) return null;
  return `${stage} rests on a decision you have since re-opened.`;
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
    next: blockedReason(campaign) ?? "—",
  };
}

import type {
  CampaignSummary,
  DnaCompleteness,
  UsageReport,
} from "@/lib/engine";
import type { StatTone } from "@/components/ui/stat-card";
import type { Status } from "@/lib/status";
import { statusLabel } from "@/lib/campaigns";

/**
 * Projects the engine's campaigns onto what Home shows.
 *
 * Home answers one question — *what needs me?* — so everything here is derived
 * from real campaign state rather than described separately. A queue item that
 * cannot be traced to a campaign the engine reported does not belong on it.
 */

export type QueueTag = "Decision" | "Setup" | "Stale";

export interface QueueItem {
  slug: string;
  tag: QueueTag;
  title: string;
  meta: string;
  cta: string;
  href: string;
}

export interface HomeStat {
  label: string;
  value: string;
  tone: StatTone;
}

export interface ActiveCampaignView {
  slug: string;
  name: string;
  status: Status;
  completed: number;
  total: number;
  stageNote: string;
}

/**
 * How many missing field names the Setup item lists before it starts counting.
 */
const MISSING_FIELDS_SHOWN = 3;

/**
 * Builds the decision queue from everything that actually needs a person.
 *
 * Four things land here. A campaign is holding at an Approval Gate, or a
 * specialist has stopped to ask the owner a question — both block a run in
 * flight, and both are tagged Decision because both are the owner's to make.
 * A campaign rests on a decision that has since been re-opened; that clears
 * itself no more than the others, which is what makes this a queue rather than
 * a status list. The last is an unfinished Brand DNA, which gates every
 * campaign stage there is, so a business with no campaigns yet still has one
 * thing waiting on it.
 *
 * Args:
 *   campaigns: The tenant's active campaigns as the engine reports them.
 *   completeness: What the Brand DNA still owes, or null when that read
 *     failed — an unread report costs this one item, not the queue.
 *
 * Returns:
 *   The queue: decisions first, since those block a run in flight; then the
 *   Brand DNA, which blocks work not yet started; then stale work.
 */
export function toQueue(
  campaigns: CampaignSummary[],
  completeness: DnaCompleteness | null,
): QueueItem[] {
  const waiting: QueueItem[] = [];
  const stale: QueueItem[] = [];

  for (const campaign of campaigns) {
    if (campaign.blocked_reason === null) continue;
    const asking = campaign.status === "awaiting_clarification";
    const deciding = asking || campaign.status === "awaiting_approval";
    let cta = "Open";
    let href = `/campaigns/${campaign.id}`;
    if (asking) {
      cta = "See questions";
      href = `/campaigns/${campaign.id}/clarifications`;
    } else if (deciding) {
      cta = "Review";
    }
    const item: QueueItem = {
      slug: campaign.id,
      tag: deciding ? "Decision" : "Stale",
      title: campaign.blocked_reason,
      meta: campaign.name,
      cta,
      href,
    };
    if (deciding) waiting.push(item);
    else stale.push(item);
  }

  const setup = toSetupItem(completeness);
  return [...waiting, ...(setup === null ? [] : [setup]), ...stale];
}

/**
 * Turns an unfinished Brand DNA into the one queue item that stands for it.
 *
 * The meta line names what is actually missing, so the business learns what it
 * owes without leaving Home. Better answers make better campaign runs, so this
 * reads as useful rather than as a demand.
 *
 * It names each field rather than the question's `label`, which is the whole
 * question text — three of those comma-separated is a paragraph, not a line.
 *
 * Args:
 *   completeness: What the Brand DNA still owes, or null when it could not be
 *     read.
 *
 * Returns:
 *   The Setup item, or null when the DNA is complete or unread.
 */
function toSetupItem(completeness: DnaCompleteness | null): QueueItem | null {
  if (completeness === null || completeness.complete) return null;

  const owed = completeness.missing.length;
  if (owed === 0) return null;

  return {
    slug: "brand-dna",
    tag: "Setup",
    title:
      completeness.required_answered === 0
        ? "Your Brand DNA is not filled in yet"
        : `${owed} answer${owed === 1 ? "" : "s"} still needed in your Brand DNA`,
    meta: describeMissing(completeness.missing.map((missing) => missing.field)),
    cta: "Fill it in",
    href: "/brand",
  };
}

/**
 * Names the first few missing fields and counts whatever is left over.
 *
 * Args:
 *   fields: The names of every Required field still owed.
 *
 * Returns:
 *   The names comma-separated, with a `+N more` tail when the list is longer
 *   than the line can carry.
 */
function describeMissing(fields: string[]): string {
  const shown = fields.slice(0, MISSING_FIELDS_SHOWN).join(", ");
  const rest = fields.length - MISSING_FIELDS_SHOWN;
  return rest > 0 ? `${shown} +${rest} more` : shown;
}

/**
 * Summarises the tenant's position in the three numbers Home leads with.
 *
 * Credits are one of them because work stops when they run out, and a business
 * owner should learn that from their own screen rather than from a refusal
 * (ADR-0020).
 *
 * Args:
 *   campaigns: The tenant's active campaigns.
 *   usage: What the tenant has spent against their credits.
 *
 * Returns:
 *   The stat tiles, in the order Home shows them.
 */
export function toStats(
  campaigns: CampaignSummary[],
  usage: UsageReport | null,
): HomeStat[] {
  const needsYou = campaigns.filter(
    (campaign) => campaign.blocked_reason !== null,
  ).length;
  const running = campaigns.filter(
    (campaign) => campaign.status === "running",
  ).length;

  const stats: HomeStat[] = [
    {
      label: "Need you",
      value: String(needsYou),
      tone: needsYou > 0 ? "primary" : "default",
    },
    { label: "In progress", value: String(running), tone: "default" },
  ];

  if (usage !== null) {
    stats.push({
      label: "Credits used",
      value: formatCredits(usage),
      tone: usage.exhausted ? "destructive" : "default",
    });
  }
  return stats;
}

/**
 * Says how many credits are gone, in the plainest terms available.
 *
 * Args:
 *   usage: The tenant's spend report.
 *
 * Returns:
 *   A percentage when there are credits to be a fraction of, and the raw
 *   spend when there are not — unlimited credits have no percentage. Whole
 *   credits either way: a fraction of a credit is display noise.
 */
function formatCredits(usage: UsageReport): string {
  if (usage.credits <= 0) return `${Math.round(usage.used)}`;
  return `${Math.round((usage.used / usage.credits) * 100)}%`;
}

/**
 * Projects campaigns onto the "in progress" list.
 *
 * Args:
 *   campaigns: The tenant's active campaigns.
 *
 * Returns:
 *   One entry per campaign that has started, in the order the engine listed
 *   them.
 */
export function toActiveCampaigns(
  campaigns: CampaignSummary[],
): ActiveCampaignView[] {
  return campaigns
    .filter((campaign) => campaign.status !== "draft")
    .map((campaign) => ({
      slug: campaign.id,
      name: campaign.name,
      status: statusLabel(campaign.status),
      completed: campaign.stage_progress.completed,
      total: campaign.stage_progress.total,
      stageNote: `${campaign.stage_progress.completed}/${campaign.stage_progress.total} stages`,
    }));
}

/**
 * Returns the width of a progress bar as a CSS percentage.
 *
 * Args:
 *   completed: How many stages are done.
 *   total: How many stages there are.
 *
 * Returns:
 *   A percentage string, `0%` when the campaign reports no stages at all.
 */
export function progressWidth(completed: number, total: number): string {
  if (total <= 0) return "0%";
  return `${Math.round((completed / total) * 100)}%`;
}

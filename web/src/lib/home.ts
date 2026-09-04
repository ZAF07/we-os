import type { CampaignSummary, UsageReport } from "@/lib/engine";
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

export type QueueTag = "Decision" | "Stale";

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
 * Builds the decision queue from campaigns that actually need a person.
 *
 * Two things put a campaign here: it is holding at an Approval Gate, or it
 * rests on a decision that has since been re-opened. Both are the owner's to
 * resolve and neither clears itself, which is what makes them a queue rather
 * than a status list.
 *
 * Args:
 *   campaigns: The tenant's active campaigns as the engine reports them.
 *
 * Returns:
 *   The queue, campaigns awaiting approval first, since those block a run.
 */
export function toQueue(campaigns: CampaignSummary[]): QueueItem[] {
  const waiting: QueueItem[] = [];
  const blocked: QueueItem[] = [];

  for (const campaign of campaigns) {
    if (campaign.blocked_reason === null) continue;
    const item: QueueItem = {
      slug: campaign.id,
      tag: campaign.status === "awaiting_approval" ? "Decision" : "Stale",
      title: campaign.blocked_reason,
      meta: campaign.name,
      cta: campaign.status === "awaiting_approval" ? "Review" : "Open",
      href: `/campaigns/${campaign.id}`,
    };
    if (campaign.status === "awaiting_approval") waiting.push(item);
    else blocked.push(item);
  }

  return [...waiting, ...blocked];
}

/**
 * Summarises the tenant's position in the three numbers Home leads with.
 *
 * Allowance is one of them because work stops when it runs out, and a business
 * owner should learn that from their own screen rather than from a refusal
 * (ADR-0020).
 *
 * Args:
 *   campaigns: The tenant's active campaigns.
 *   usage: What the tenant has spent against their allowance.
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
      label: "Allowance used",
      value: formatAllowance(usage),
      tone: usage.exhausted ? "destructive" : "default",
    });
  }
  return stats;
}

/**
 * Says how much of the allowance is gone, in the plainest terms available.
 *
 * Args:
 *   usage: The tenant's spend report.
 *
 * Returns:
 *   A percentage when there is an allowance to be a fraction of, and the raw
 *   spend when there is not — an unlimited allowance has no percentage.
 */
function formatAllowance(usage: UsageReport): string {
  if (usage.allowance <= 0) return `${usage.used.toFixed(2)}`;
  return `${Math.round((usage.used / usage.allowance) * 100)}%`;
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

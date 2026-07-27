import type { CampaignRow } from "@/lib/mock-data";

export interface CreatedCampaign {
  slug: string;
  name: string;
  reason: string;
  owner: string;
  objective: string;
  action: string;
  metric: string;
  audience: string;
  funnel: string;
  offer: string;
  cta: string;
  budget: string;
  start: string;
  end: string;
  channels: string[];
}

/**
 * Converts a campaign name into a unique route slug.
 *
 * Args:
 *   name: The campaign display name.
 *   taken: Slugs already in use.
 *
 * Returns:
 *   A kebab-case slug, suffixed with a counter on collision.
 */
export function slugify(name: string, taken: string[]): string {
  const base =
    name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "campaign";
  let slug = base;
  let counter = 2;
  while (taken.includes(slug)) {
    slug = `${base}-${counter}`;
    counter += 1;
  }
  return slug;
}

/**
 * Projects a created campaign onto a Campaigns-table row.
 *
 * Args:
 *   campaign: A campaign created through the wizard.
 *
 * Returns:
 *   The table row: a Draft campaign sitting at the Brief stage.
 */
export function createdCampaignToRow(campaign: CreatedCampaign): CampaignRow {
  return {
    slug: campaign.slug,
    name: campaign.name,
    objective: campaign.objective,
    stage: "Brief",
    stageNum: "1/8",
    status: "Draft",
    next: "Review brief",
    updated: "Just now",
  };
}

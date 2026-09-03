"use server";

import { revalidatePath } from "next/cache";

import {
  archiveCampaign,
  createCampaign,
  getAudienceSegments,
  getCampaign,
  listCampaigns,
  EngineError,
  type Campaign,
  type CampaignGoalInput,
  type CampaignSummary,
} from "@/lib/engine";

export interface CreateResult {
  campaign: Campaign | null;
  error: string | null;
}

/**
 * Loads the audience segments a new campaign may target.
 *
 * A campaign targets one of the segments the business described in its Brand
 * DNA, never free text, so the wizard offers exactly what the engine reports.
 *
 * Returns:
 *   The segment names, empty when the Brand DNA names none yet.
 */
export async function loadAudienceSegments(): Promise<string[]> {
  const { segments } = await getAudienceSegments();
  return segments;
}

/**
 * Loads the tenant's active campaigns for the portfolio table.
 *
 * Returns:
 *   One summary per active campaign.
 */
export async function loadCampaigns(): Promise<CampaignSummary[]> {
  const { campaigns } = await listCampaigns();
  return campaigns;
}

/**
 * Creates a campaign from the goal the wizard collected.
 *
 * The engine refuses an incomplete goal by naming the fields it is missing, so
 * that message is surfaced as-is rather than replaced with a generic one.
 *
 * Args:
 *   goal: The campaign goal.
 *
 * Returns:
 *   The created campaign, or the engine's message explaining what was refused.
 */
export async function createCampaignAction(
  goal: CampaignGoalInput,
): Promise<CreateResult> {
  try {
    const campaign = await createCampaign(goal);
    revalidatePath("/campaigns");
    return { campaign, error: null };
  } catch (error) {
    if (error instanceof EngineError) {
      return { campaign: null, error: error.message };
    }
    throw error;
  }
}

/**
 * Archives a campaign so it leaves the active list.
 *
 * Args:
 *   slug: The campaign slug.
 */
export async function archiveCampaignAction(slug: string): Promise<void> {
  await archiveCampaign(slug);
  revalidatePath("/campaigns");
}

/**
 * Loads one campaign for its Workspace.
 *
 * Args:
 *   slug: The campaign slug.
 *
 * Returns:
 *   The campaign, or null when the tenant owns no such campaign.
 */
export async function loadCampaign(slug: string): Promise<Campaign | null> {
  try {
    return await getCampaign(slug);
  } catch (error) {
    if (error instanceof EngineError && error.status === 404) return null;
    throw error;
  }
}

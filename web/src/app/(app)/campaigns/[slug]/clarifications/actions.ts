"use server";

import {
  getCampaign,
  getRunClarifications,
  listActiveRuns,
  EngineError,
  type Campaign,
  type RunClarifications,
} from "@/lib/engine";

export interface ClarificationsView {
  campaign: Campaign;
  pending: RunClarifications | null;
}

/**
 * Loads a campaign and the questions its live run is asking, if it is asking.
 *
 * The questions are read from the run, since that is where they are held: a
 * campaign with no live run, or whose run is at an Approval Gate or still
 * working, has none to show, and the screen says so rather than inventing an
 * empty form.
 *
 * Args:
 *   slug: The campaign slug.
 *
 * Returns:
 *   The campaign and its pending questions (null when nothing is asked), or
 *   null when the tenant owns no such campaign.
 */
export async function loadClarifications(
  slug: string,
): Promise<ClarificationsView | null> {
  let campaign: Campaign;
  try {
    campaign = await getCampaign(slug);
  } catch (error) {
    if (error instanceof EngineError && error.status === 404) return null;
    throw error;
  }
  const { runs } = await listActiveRuns();
  const active = runs.find((run) => run.slug === slug);
  if (!active) return { campaign, pending: null };
  try {
    return { campaign, pending: await getRunClarifications(active.run_id) };
  } catch (error) {
    if (error instanceof EngineError && error.status === 409) {
      return { campaign, pending: null };
    }
    throw error;
  }
}

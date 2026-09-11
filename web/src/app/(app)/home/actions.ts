"use server";

import {
  getBrandDnaCompleteness,
  getDnaReview,
  getMe,
  getUsage,
  listCampaigns,
  nullOnEngineError,
  type CampaignSummary,
  type DnaCompleteness,
  type DnaReview,
  type UsageReport,
} from "@/lib/engine";

export interface HomeData {
  campaigns: CampaignSummary[];
  usage: UsageReport | null;
  completeness: DnaCompleteness | null;
  review: DnaReview | null;
  tier: string | null;
}

/**
 * Loads what Home renders: the tenant's campaigns, their spend, and the tier.
 *
 * Usage is loaded alongside rather than separately because Home is where a
 * business owner should learn their credits are running down — before work
 * stops, not when a run is refused (ADR-0020). It is optional: a usage read
 * that fails should cost the credits tile, not the whole screen.
 *
 * The tier is read here, and only here, because Home is the one route a new
 * business is sent to. A tenant whose tier was never recorded — the window
 * between activating the Organization and the tier call, lived in only when
 * that call failed and the person left — is sent back to finish rather than
 * shown a Home it has not finished setting up (ADR-0027).
 *
 * Brand DNA completeness comes along for the same reason: a complete Brand DNA
 * gates every campaign stage there is, so an unfinished one is the one thing
 * waiting on a business that has no campaigns yet. It is optional too — a read
 * that fails costs the queue item, not the screen. The `(app)` layout reads the
 * same report for its nav badge, so a Home render makes the call twice; that is
 * a deliberate trade, made in the layout's own docstring.
 *
 * Whether the Brand DNA is due a review is read for the same reason: it is the
 * one thing waiting on a business whose campaigns are all fine (ADR-0028).
 * Optional too, costing the Review item alone.
 *
 * Returns:
 *   The campaigns, the usage report (null when it could not be read), what the
 *   Brand DNA still owes (null when that could not be read), whether it is due
 *   a review (null when that could not be read), and the tier the business
 *   recorded (null when it never did).
 *
 * Throws:
 *   EngineError: When the campaigns or the tier cannot be read, since there
 *     is no useful Home without them.
 */
export async function loadHome(): Promise<HomeData> {
  const [{ campaigns }, usage, completeness, review, me] = await Promise.all([
    listCampaigns(),
    getUsage().catch(nullOnEngineError),
    getBrandDnaCompleteness().catch(nullOnEngineError),
    getDnaReview().catch(nullOnEngineError),
    getMe(),
  ]);
  return { campaigns, usage, completeness, review, tier: me.tier };
}

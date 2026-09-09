"use server";

import {
  getMe,
  getUsage,
  listCampaigns,
  EngineError,
  type CampaignSummary,
  type UsageReport,
} from "@/lib/engine";

export interface HomeData {
  campaigns: CampaignSummary[];
  usage: UsageReport | null;
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
 * Returns:
 *   The campaigns, the usage report (null when it could not be read), and the
 *   tier the business recorded (null when it never did).
 *
 * Throws:
 *   EngineError: When the campaigns or the tier cannot be read, since there
 *     is no useful Home without them.
 */
export async function loadHome(): Promise<HomeData> {
  const [{ campaigns }, usage, me] = await Promise.all([
    listCampaigns(),
    getUsage().catch((error: unknown) => {
      if (error instanceof EngineError) return null;
      throw error;
    }),
    getMe(),
  ]);
  return { campaigns, usage, tier: me.tier };
}

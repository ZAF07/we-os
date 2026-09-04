"use server";

import {
  getUsage,
  listCampaigns,
  EngineError,
  type CampaignSummary,
  type UsageReport,
} from "@/lib/engine";

export interface HomeData {
  campaigns: CampaignSummary[];
  usage: UsageReport | null;
}

/**
 * Loads what Home renders: the tenant's campaigns and their spend.
 *
 * Usage is loaded alongside rather than separately because Home is where a
 * business owner should learn their allowance is running down — before work
 * stops, not when a run is refused (ADR-0020). It is optional: a usage read
 * that fails should cost the allowance tile, not the whole screen.
 *
 * Returns:
 *   The campaigns and the usage report, the latter null when it could not be
 *   read.
 *
 * Throws:
 *   EngineError: When the campaigns themselves cannot be read, since there is
 *     no useful Home without them.
 */
export async function loadHome(): Promise<HomeData> {
  const [{ campaigns }, usage] = await Promise.all([
    listCampaigns(),
    getUsage().catch((error: unknown) => {
      if (error instanceof EngineError) return null;
      throw error;
    }),
  ]);
  return { campaigns, usage };
}

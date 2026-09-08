"use server";

import {
  getStageDeliverable,
  listCampaigns,
  EngineError,
  type StageDeliverable,
} from "@/lib/engine";
import { deliverableName } from "@/lib/workspace";

export interface PerformancePlanView {
  slug: string;
  name: string;
  stale: boolean;
  content: string;
}

export interface PerformanceData {
  plans: PerformancePlanView[];
  campaignCount: number;
}

/**
 * Loads every Performance Plan the tenant's campaigns have produced.
 *
 * This screen reports the **plan**, not measured results: nothing has been
 * published yet, so there are no results to report and inventing them would be
 * fiction. What it can honestly show is what the performance specialist decided
 * — the channel mix, the spend allocation, the placements, the KPI targets.
 *
 * Returns:
 *   One entry per campaign that has produced a plan, plus how many campaigns
 *   exist at all — so an empty screen can say which of the two situations it is
 *   in: no campaigns, or none that have reached the Plan stage.
 */
export async function loadPerformance(): Promise<PerformanceData> {
  const { campaigns } = await listCampaigns();
  const name = deliverableName("performance-plan");

  const loaded = await Promise.all(
    campaigns.map(async (campaign) => {
      try {
        const plan: StageDeliverable = await getStageDeliverable(
          campaign.id,
          name,
        );
        return {
          slug: campaign.id,
          name: campaign.name,
          stale: plan.stale,
          content: plan.content,
        };
      } catch (error) {
        if (error instanceof EngineError && error.status === 404) return null;
        throw error;
      }
    }),
  );

  return {
    plans: loaded.filter((plan): plan is PerformancePlanView => plan !== null),
    campaignCount: campaigns.length,
  };
}

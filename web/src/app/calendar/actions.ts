"use server";

import { getCampaign, listCampaigns, EngineError } from "@/lib/engine";

export interface ScheduledCampaign {
  slug: string;
  name: string;
  status: string;
  startDate: string;
  endDate: string;
  completed: number;
  total: number;
}

/**
 * Loads the campaign timeframes the Calendar lays out.
 *
 * Publishing and scheduling arrive in a later PRD, so there are no post
 * schedules to show. What genuinely exists at this stage is when each campaign
 * is meant to run, which is what a business owner planning their quarter
 * actually needs — and it is real, which fabricated post times would not be.
 *
 * Returns:
 *   One entry per campaign that has a timeframe, earliest start first.
 */
export async function loadCalendar(): Promise<ScheduledCampaign[]> {
  const { campaigns } = await listCampaigns();

  const scheduled = await Promise.all(
    campaigns.map(async (summary) => {
      try {
        const campaign = await getCampaign(summary.id);
        return {
          slug: summary.id,
          name: campaign.name,
          status: campaign.status,
          startDate: campaign.timeframe.start_date,
          endDate: campaign.timeframe.end_date,
          completed: summary.stage_progress.completed,
          total: summary.stage_progress.total,
        };
      } catch (error) {
        if (error instanceof EngineError && error.status === 404) return null;
        throw error;
      }
    }),
  );

  return scheduled
    .filter((entry): entry is ScheduledCampaign => entry !== null)
    .sort((a, b) => a.startDate.localeCompare(b.startDate));
}

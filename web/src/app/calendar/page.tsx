import Link from "next/link";

import { Card, CardHeader } from "@/components/ui/card";
import { StatusPill } from "@/components/ui/status-pill";
import { formatRange } from "@/lib/calendar";
import { statusLabel } from "@/lib/campaigns";
import { engineErrorMessage } from "@/lib/engine";

import { loadCalendar, type ScheduledCampaign } from "./actions";

export const dynamic = "force-dynamic";

/**
 * Renders the Calendar: when each campaign is planned to run.
 *
 * Not a publishing schedule — publishing arrives in a later PRD, and inventing
 * post times would be fiction. What exists now is each campaign's timeframe and
 * how far through the pipeline it has got, which is what someone planning a
 * quarter can actually act on.
 */
export default async function CalendarPage() {
  let campaigns: ScheduledCampaign[];
  try {
    campaigns = await loadCalendar();
  } catch (error) {
    return (
      <Shell>
        <p role="alert" className="text-[13px] text-muted-foreground">
          {engineErrorMessage(error)}
        </p>
      </Shell>
    );
  }

  if (campaigns.length === 0) {
    return (
      <Shell>
        <Card className="px-[22px] py-5">
          <div className="text-sm font-bold">Nothing scheduled</div>
          <p className="mt-1.5 text-[13px] text-muted-foreground">
            Campaigns appear here with their planned timeframe as soon as you
            create one. Start from{" "}
            <Link href="/campaigns" className="font-semibold text-primary">
              Campaigns
            </Link>
            .
          </p>
        </Card>
      </Shell>
    );
  }

  return (
    <Shell>
      <Card>
        <CardHeader title="Planned timeframes" />
        <ul>
          {campaigns.map((campaign) => (
            <li key={campaign.slug}>
              <Link
                href={`/campaigns/${campaign.slug}`}
                className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-slate-100 px-[18px] py-3.5 hover:bg-slate-50"
              >
                <div className="min-w-[180px] flex-1">
                  <div className="text-[13.5px] font-semibold">
                    {campaign.name}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {formatRange(campaign.startDate, campaign.endDate)}
                  </div>
                </div>
                <div className="text-xs whitespace-nowrap text-muted-foreground">
                  {campaign.completed}/{campaign.total} stages
                </div>
                <StatusPill status={statusLabel(campaign.status)} />
              </Link>
            </li>
          ))}
        </ul>
      </Card>

      <p className="mt-4 rounded-xl border border-dashed border-slate-300 bg-slate-50 px-[18px] py-3.5 text-[13px] text-muted-foreground">
        <strong className="text-slate-700">Not here yet:</strong> per-post
        scheduling. Once campaigns can be published, the individual creative
        units and their send times will fill this screen alongside the
        timeframes.
      </p>
    </Shell>
  );
}

/**
 * Renders the page frame and the heading that says what this screen is.
 *
 * Args:
 *   children: The page body.
 */
function Shell({ children }: { children: React.ReactNode }) {
  return (
    <main className="flex-1 overflow-y-auto px-4 py-6 md:px-8 md:py-7">
      <div className="max-w-[880px]">
        <h1 className="text-[22px] font-bold tracking-tight">Calendar</h1>
        <p className="mt-1 mb-[18px] text-[13px] text-muted-foreground">
          When each campaign is planned to run, and how far through the pipeline
          it has got.
        </p>
        {children}
      </div>
    </main>
  );
}

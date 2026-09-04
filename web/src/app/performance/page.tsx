import Link from "next/link";

import { Card, CardHeader } from "@/components/ui/card";
import { StatusPill } from "@/components/ui/status-pill";
import { EngineError } from "@/lib/engine";

import { loadPerformance, type PerformancePlanView } from "./actions";

export const dynamic = "force-dynamic";

/**
 * Renders Performance: the channel and spend decisions, per campaign.
 *
 * Deliberately *not* a results dashboard. Publishing arrives in a later PRD, so
 * there is nothing measured to report — and a screen showing invented
 * impressions would be worse than one showing none. What it reports is the
 * Performance Plan: what the specialist decided, and why.
 */
export default async function PerformancePage() {
  let data;
  try {
    data = await loadPerformance();
  } catch (error) {
    const message =
      error instanceof EngineError
        ? error.message
        : "Could not reach the engine. Is it running on ENGINE_BASE_URL?";
    return (
      <Shell>
        <p role="alert" className="text-[13px] text-muted-foreground">
          {message}
        </p>
      </Shell>
    );
  }

  if (data.plans.length === 0) {
    return (
      <Shell>
        <Card className="px-[22px] py-5">
          <div className="text-sm font-bold">Nothing planned yet</div>
          <p className="mt-1.5 text-[13px] text-muted-foreground">
            {data.campaignCount === 0 ? (
              <>
                You have no campaigns. Start one from{" "}
                <Link href="/campaigns" className="font-semibold text-primary">
                  Campaigns
                </Link>
                , and its channel mix, spend allocation and KPI targets appear
                here once the Plan stage runs.
              </>
            ) : (
              <>
                None of your campaigns has reached the Plan stage. The channel
                mix and spend allocation are decided there, after strategy is
                approved — see{" "}
                <Link href="/campaigns" className="font-semibold text-primary">
                  Campaigns
                </Link>
                .
              </>
            )}
          </p>
        </Card>
      </Shell>
    );
  }

  return (
    <Shell>
      <div className="flex flex-col gap-4">
        {data.plans.map((plan) => (
          <PlanCard key={plan.slug} plan={plan} />
        ))}
      </div>
    </Shell>
  );
}

/**
 * Renders one campaign's Performance Plan.
 *
 * Args:
 *   plan: The plan and the campaign it belongs to.
 */
function PlanCard({ plan }: { plan: PerformancePlanView }) {
  return (
    <Card>
      <CardHeader
        title={plan.name}
        action={
          <div className="flex items-center gap-2">
            {plan.stale && <StatusPill status="Stale" />}
            <Link
              href={`/campaigns/${plan.slug}`}
              className="px-1 text-xs font-semibold text-primary"
            >
              Open →
            </Link>
          </div>
        }
      />
      {plan.stale && (
        <p className="mx-[18px] mb-2 rounded-lg border border-orange-200 bg-orange-50 px-3 py-2 text-[12.5px] text-orange-900">
          This plan rests on a decision that has since been re-opened. Re-run
          the stage from the campaign to bring it up to date.
        </p>
      )}
      <article
        aria-label={`Performance plan for ${plan.name}`}
        className="px-[18px] pb-4 text-[13.5px] leading-relaxed whitespace-pre-wrap text-slate-800"
      >
        {plan.content}
      </article>
    </Card>
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
        <h1 className="text-[22px] font-bold tracking-tight">Performance</h1>
        <p className="mt-1 mb-[18px] text-[13px] text-muted-foreground">
          What each campaign <strong>plans</strong> to do — channels, spend
          allocation, placements and KPI targets. These are decisions, not
          measurements: nothing has been published yet, so there are no results
          to report.
        </p>
        {children}
      </div>
    </main>
  );
}

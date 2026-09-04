import Link from "next/link";

import { Card, CardHeader } from "@/components/ui/card";
import { StatCard } from "@/components/ui/stat-card";
import { StatusPill } from "@/components/ui/status-pill";
import {
  EngineError,
  type CampaignSummary,
  type UsageReport,
} from "@/lib/engine";
import {
  progressWidth,
  toActiveCampaigns,
  toQueue,
  toStats,
  type QueueTag,
} from "@/lib/home";
import { statusPillClasses } from "@/lib/status";
import { cn } from "@/lib/utils";

import { loadHome } from "./actions";

export const dynamic = "force-dynamic";

const TAG_CLASSES: Record<QueueTag, string> = {
  Decision: "bg-indigo-50 text-indigo-700",
  Blocked: statusPillClasses("Stale"),
};

/**
 * Renders Home: what needs the business owner, and what is under way.
 *
 * Everything comes from the engine, scoped to the tenant its verified claim
 * names. A screen that answers "what needs me?" is only worth anything if the
 * answer is true, so nothing here is filled in when the real data is absent —
 * it says so instead.
 */
export default async function HomePage() {
  let data;
  try {
    data = await loadHome();
  } catch (error) {
    return <EngineDown error={error} />;
  }

  const { campaigns, usage } = data;
  const queue = toQueue(campaigns);
  const active = toActiveCampaigns(campaigns);

  return (
    <main className="flex-1 overflow-y-auto px-4 py-6 md:px-8 md:py-7">
      <div className="mb-5 flex max-w-[1120px] flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-[22px] font-bold tracking-tight">Home</h1>
          <p className="mt-1 text-[13px] text-muted-foreground">
            {queue.length === 0
              ? "Nothing is waiting on you."
              : `${queue.length} thing${queue.length === 1 ? "" : "s"} need you.`}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {toStats(campaigns, usage).map((stat) => (
            <StatCard
              key={stat.label}
              label={stat.label}
              value={stat.value}
              tone={stat.tone}
            />
          ))}
        </div>
      </div>

      <div className="grid max-w-[1120px] grid-cols-[repeat(auto-fit,minmax(400px,1fr))] items-start gap-5 max-sm:grid-cols-1">
        <div className="flex flex-col gap-5">
          <ActionQueue queue={queue} />
          <InProgress campaigns={active} />
        </div>
        <div className="flex flex-col gap-5">
          <AllowanceCard usage={usage} />
          <Portfolio campaigns={campaigns} />
        </div>
      </div>
    </main>
  );
}

/**
 * Renders the decision queue.
 *
 * Args:
 *   queue: What needs the owner, approvals first.
 */
function ActionQueue({ queue }: { queue: ReturnType<typeof toQueue> }) {
  return (
    <Card>
      <CardHeader
        title="Action queue"
        action={
          <div className="text-xs text-muted-foreground">
            {queue.length} item{queue.length === 1 ? "" : "s"}
          </div>
        }
      />
      {queue.length === 0 ? (
        <p className="px-[18px] py-4 text-[13px] text-muted-foreground">
          Nothing is waiting on a decision. When a campaign reaches an approval
          gate, or work goes stale because you re-opened something upstream, it
          appears here.
        </p>
      ) : (
        queue.map((item) => (
          <div
            key={item.slug}
            className="flex flex-wrap items-center gap-x-3.5 gap-y-2.5 border-b border-slate-100 px-[18px] py-[13px] hover:bg-slate-50"
          >
            <span
              className={cn(
                "rounded-md px-2 py-0.5 text-[11px] font-semibold whitespace-nowrap",
                TAG_CLASSES[item.tag],
              )}
            >
              {item.tag}
            </span>
            <div className="min-w-[200px] flex-1">
              <div className="text-[13.5px] font-semibold">{item.title}</div>
              <div className="text-xs text-muted-foreground">{item.meta}</div>
            </div>
            <Link
              href={item.href}
              className="ml-auto shrink-0 rounded-lg border bg-card px-3 py-[5px] text-[12.5px] font-semibold whitespace-nowrap hover:border-indigo-200 hover:bg-indigo-50 hover:text-primary"
            >
              {item.cta}
            </Link>
          </div>
        ))
      )}
    </Card>
  );
}

/**
 * Renders the campaigns currently under way.
 *
 * Args:
 *   campaigns: The campaigns that have started.
 */
function InProgress({
  campaigns,
}: {
  campaigns: ReturnType<typeof toActiveCampaigns>;
}) {
  return (
    <Card>
      <CardHeader title="In progress now" />
      {campaigns.length === 0 ? (
        <p className="px-[18px] py-4 text-[13px] text-muted-foreground">
          No campaign is running. Start one from{" "}
          <Link href="/campaigns" className="font-semibold text-primary">
            Campaigns
          </Link>
          .
        </p>
      ) : (
        campaigns.map((campaign) => (
          <Link
            key={campaign.slug}
            href={`/campaigns/${campaign.slug}`}
            className="block border-b border-slate-100 px-[18px] py-[13px] hover:bg-slate-50"
          >
            <div className="flex items-center gap-2.5">
              <div className="flex-1 text-[13.5px] font-semibold">
                {campaign.name}
              </div>
              <StatusPill status={campaign.status} />
            </div>
            <div className="mt-[7px] flex items-center gap-2.5">
              <div className="h-1 flex-1 overflow-hidden rounded-full bg-slate-100">
                <div
                  className="h-full rounded-full bg-primary"
                  style={{
                    width: progressWidth(campaign.completed, campaign.total),
                  }}
                />
              </div>
              <div className="text-xs whitespace-nowrap text-muted-foreground">
                {campaign.stageNote}
              </div>
            </div>
          </Link>
        ))
      )}
    </Card>
  );
}

/**
 * Renders what the business has spent against its allowance.
 *
 * Args:
 *   usage: The spend report, or null when it could not be read.
 */
function AllowanceCard({ usage }: { usage: UsageReport | null }) {
  if (usage === null) {
    return (
      <Card className="px-[18px] py-4">
        <div className="text-sm font-bold">Allowance</div>
        <p className="mt-1 text-[12.5px] text-muted-foreground">
          Could not read your usage just now. Everything else on this page is
          current.
        </p>
      </Card>
    );
  }

  const unlimited = usage.allowance <= 0;
  const spent = unlimited
    ? 0
    : Math.min(100, Math.round((usage.used / usage.allowance) * 100));

  return (
    <Card className="px-[18px] py-4">
      <div className="flex items-center justify-between">
        <div className="text-sm font-bold">Allowance</div>
        {usage.exhausted && <StatusPill status="Needs attention" />}
      </div>
      {unlimited ? (
        <p className="mt-2 text-[12.5px] text-muted-foreground">
          Spent {usage.used.toFixed(2)} so far. No ceiling is set on this
          business.
        </p>
      ) : (
        <>
          <div className="mt-2.5 h-1.5 overflow-hidden rounded-full bg-slate-100">
            <div
              className={cn(
                "h-full rounded-full",
                usage.exhausted ? "bg-destructive" : "bg-primary",
              )}
              style={{ width: `${spent}%` }}
            />
          </div>
          <p className="mt-2 text-[12.5px] text-muted-foreground">
            {usage.exhausted
              ? "Spent. Work resumes when your allowance renews."
              : `${spent}% used — ${usage.remaining.toFixed(2)} left.`}
          </p>
        </>
      )}
      {usage.campaigns.length > 0 && (
        <div className="mt-3 border-t border-slate-100 pt-2.5">
          <div className="mb-1.5 text-[11px] font-bold tracking-wide text-muted-foreground uppercase">
            Where it went
          </div>
          {usage.campaigns.map((campaign) => (
            <div
              key={campaign.slug}
              className="flex justify-between py-[3px] text-[12.5px]"
            >
              <span className="truncate text-muted-foreground">
                {campaign.slug}
              </span>
              <span className="font-semibold">{campaign.used.toFixed(2)}</span>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

/**
 * Renders a compact count of the whole portfolio by lifecycle status.
 *
 * Args:
 *   campaigns: Every active campaign the tenant owns.
 */
function Portfolio({ campaigns }: { campaigns: CampaignSummary[] }) {
  const counts = new Map<string, number>();
  for (const campaign of campaigns) {
    counts.set(campaign.status, (counts.get(campaign.status) ?? 0) + 1);
  }

  return (
    <Card>
      <CardHeader
        title="Portfolio"
        action={
          <Link
            href="/campaigns"
            className="px-1 text-xs font-semibold text-primary"
          >
            View all →
          </Link>
        }
      />
      <div className="px-[18px] py-3">
        {campaigns.length === 0 ? (
          <p className="text-[13px] text-muted-foreground">No campaigns yet.</p>
        ) : (
          [...counts.entries()].map(([status, count]) => (
            <div key={status} className="flex justify-between py-1 text-[13px]">
              <span className="text-muted-foreground">{status}</span>
              <span className="font-semibold">{count}</span>
            </div>
          ))
        )}
      </div>
    </Card>
  );
}

/**
 * Renders the page when the engine could not be reached.
 *
 * Args:
 *   error: What went wrong.
 */
function EngineDown({ error }: { error: unknown }) {
  const message =
    error instanceof EngineError
      ? error.message
      : "Could not reach the engine. Is it running on ENGINE_BASE_URL?";
  return (
    <main className="flex-1 overflow-y-auto px-4 py-6 md:px-8 md:py-7">
      <h1 className="text-[22px] font-bold tracking-tight">Home</h1>
      <p role="alert" className="mt-2 text-[13px] text-muted-foreground">
        {message}
      </p>
    </main>
  );
}

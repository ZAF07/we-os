"use client";

import Link from "next/link";

import { Card, CardHeader } from "@/components/ui/card";
import { StatCard } from "@/components/ui/stat-card";
import { StatusPill } from "@/components/ui/status-pill";
import {
  activeCampaigns,
  BLOCKED_ITEMS,
  FINDINGS,
  HOME_PERF_STATS,
  homeStats,
  queueItems,
  RECOMMENDATIONS,
  shortTitle,
  upcomingItems,
  type QueueTag,
} from "@/lib/mock-data";
import { statusPillClasses } from "@/lib/status";
import { useDemoStore } from "@/lib/store";
import { cn } from "@/lib/utils";

const TAG_CLASSES: Record<QueueTag, string> = {
  Decision: "bg-indigo-50 text-indigo-700",
  Flagged: statusPillClasses("Needs attention"),
  "Needs input": statusPillClasses("Needs input"),
};

/**
 * Builds a click handler that pre-selects a Brand section before a
 * CTA navigates there, or undefined when the CTA has no section.
 *
 * Args:
 *   brandSection: The Brand section index the CTA targets, if any.
 *   setBrandIdx: The store action that selects a Brand section.
 *
 * Returns:
 *   An onClick handler, or undefined.
 */
function brandSectionClick(
  brandSection: number | undefined,
  setBrandIdx: (index: number) => void,
): (() => void) | undefined {
  if (brandSection === undefined) return undefined;
  return () => setBrandIdx(brandSection);
}

/** Renders the prioritized decision/approval queue with per-item CTAs. */
function ActionQueue() {
  const approved = useDemoStore((state) => state.approved);
  const setBrandIdx = useDemoStore((state) => state.setBrandIdx);
  const queue = queueItems(approved);

  return (
    <Card>
      <CardHeader
        title="Action queue"
        action={
          <div className="text-xs text-muted-foreground">
            {queue.length} items need you
          </div>
        }
      />
      {queue.map((item) => (
        <div
          key={item.key}
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
          <div className="ml-auto flex shrink-0 items-center gap-3">
            <span className="text-xs whitespace-nowrap text-muted-foreground">
              {item.due}
            </span>
            <Link
              href={item.href}
              onClick={brandSectionClick(item.brandSection, setBrandIdx)}
              className="rounded-lg border bg-card px-3 py-[5px] text-[12.5px] font-semibold whitespace-nowrap hover:border-indigo-200 hover:bg-indigo-50 hover:text-primary"
            >
              {item.cta}
            </Link>
          </div>
        </div>
      ))}
    </Card>
  );
}

/** Renders the active-campaigns list with status and progress. */
function InProgress() {
  const approved = useDemoStore((state) => state.approved);

  return (
    <Card>
      <CardHeader title="In progress now" />
      {activeCampaigns(approved).map((campaign) => (
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
                style={{ width: campaign.pct }}
              />
            </div>
            <div className="text-xs whitespace-nowrap text-muted-foreground">
              {campaign.stageNote}
            </div>
          </div>
        </Link>
      ))}
    </Card>
  );
}

/** Renders the blocked-work list with unblocking CTAs. */
function Blocked() {
  const setBrandIdx = useDemoStore((state) => state.setBrandIdx);

  return (
    <Card>
      <CardHeader title="Blocked" />
      {BLOCKED_ITEMS.map((item) => (
        <div
          key={item.title}
          className="flex items-center gap-3 border-b border-slate-100 px-[18px] py-3"
        >
          <span className="size-2 shrink-0 rounded-full bg-destructive" />
          <div className="flex-1">
            <div className="text-[13.5px] font-semibold">{item.title}</div>
            <div className="text-xs text-muted-foreground">{item.reason}</div>
          </div>
          <Link
            href={item.href}
            onClick={brandSectionClick(item.brandSection, setBrandIdx)}
            className="rounded-md px-1.5 py-1 text-[12.5px] font-semibold text-primary hover:bg-indigo-50"
          >
            {item.cta}
          </Link>
        </div>
      ))}
    </Card>
  );
}

/** Renders the 28-day performance summary panel. */
function PerformanceSummary() {
  return (
    <Card className="px-[18px] py-4">
      <div className="flex items-center justify-between">
        <div className="text-sm font-bold">Performance · 28 days</div>
        <Link
          href="/performance"
          className="px-1 text-xs font-semibold text-primary"
        >
          Breakdown →
        </Link>
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2">
        {HOME_PERF_STATS.map((stat) => (
          <div key={stat.label}>
            <div className="text-[11.5px] text-muted-foreground">
              {stat.label}
            </div>
            <div className="text-base font-bold">{stat.value}</div>
            <div className="text-[11.5px] font-semibold text-emerald-700">
              {stat.delta}
            </div>
          </div>
        ))}
      </div>
      <div className="mt-3 border-t border-slate-100 pt-2.5 text-[12.5px] text-muted-foreground">
        Improving: email-driven repeat purchases{" "}
        <strong className="text-emerald-700">+18%</strong> since the
        refill-economics angle shipped.
      </div>
    </Card>
  );
}

/** Renders the upcoming scheduled-content list. */
function Upcoming() {
  return (
    <Card>
      <CardHeader
        title="Scheduled next"
        action={
          <Link
            href="/calendar"
            className="px-1 text-xs font-semibold text-primary"
          >
            Calendar →
          </Link>
        }
      />
      {upcomingItems().map((item) => (
        <div
          key={item.day}
          className="flex items-center gap-2.5 border-b border-slate-100 px-[18px] py-2.5"
        >
          <div className="w-[38px] shrink-0 text-center">
            <div className="text-[10px] font-bold text-muted-foreground uppercase">
              {item.dow}
            </div>
            <div className="text-[15px] font-bold">{item.day}</div>
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate text-[13px] font-semibold">
              {shortTitle(item.title)}
            </div>
            <div className="text-[11.5px] text-muted-foreground">
              {item.channel}
            </div>
          </div>
          <StatusPill status={item.status} className="px-[7px] text-[10.5px]" />
        </div>
      ))}
    </Card>
  );
}

/** Renders the recent research findings panel. */
function Findings() {
  return (
    <Card className="px-[18px] py-4">
      <div className="mb-2.5 text-sm font-bold">Recent findings</div>
      <div className="flex flex-col gap-2.5">
        {FINDINGS.map((finding) => (
          <div
            key={finding.src}
            className="border-l-2 border-indigo-200 pl-2.5"
          >
            <div className="text-[12.5px]">{finding.text}</div>
            <div className="mt-0.5 text-[11px] text-muted-foreground">
              {finding.src}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

/** Renders the recommended-next-actions panel. */
function Recommended() {
  return (
    <section className="rounded-xl border border-indigo-200 bg-indigo-50 px-[18px] py-4">
      <div className="mb-2 text-sm font-bold text-indigo-900">
        Recommended next
      </div>
      <div className="flex flex-col gap-2">
        {RECOMMENDATIONS.map((reco) => (
          <Link
            key={reco.text}
            href={reco.href}
            className="flex items-center gap-2 rounded-lg border border-indigo-200 bg-card px-3 py-[9px] text-left text-[12.5px] font-semibold hover:border-primary"
          >
            <span className="text-primary">→</span> {reco.text}
          </Link>
        ))}
      </div>
    </section>
  );
}

/** Renders the Home screen: stats, queue, campaigns, and signals. */
export default function HomePage() {
  const approved = useDemoStore((state) => state.approved);

  return (
    <main className="flex-1 overflow-y-auto px-4 py-6 md:px-8 md:py-7">
      <div className="mb-5 flex max-w-[1120px] flex-wrap items-end justify-between gap-4">
        <div>
          <div className="text-xs font-semibold tracking-wider text-muted-foreground uppercase">
            Wednesday, July 16
          </div>
          <h1 className="mt-1 text-[22px] font-bold tracking-tight">
            Good morning, Maya
          </h1>
        </div>
        <div className="flex flex-wrap gap-2">
          {homeStats(approved).map((stat) => (
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
          <ActionQueue />
          <InProgress />
          <Blocked />
        </div>
        <div className="flex flex-col gap-5">
          <PerformanceSummary />
          <Upcoming />
          <Findings />
          <Recommended />
        </div>
      </div>
    </main>
  );
}

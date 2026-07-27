"use client";

import Link from "next/link";

import { Card } from "@/components/ui/card";
import { StatusPill } from "@/components/ui/status-pill";
import {
  CALENDAR_ITEMS,
  campaignSlugForName,
  shortTitle,
  type CalendarItem,
} from "@/lib/mock-data";
import { statusEdgeClass, statusPillClasses } from "@/lib/status";
import { useDemoStore, type CalendarMode } from "@/lib/store";
import { cn } from "@/lib/utils";

const MODES: Array<{ key: CalendarMode; label: string }> = [
  { key: "calendar", label: "Calendar" },
  { key: "list", label: "List" },
  { key: "campaign", label: "By campaign" },
];

const DOWS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

interface CalendarCell {
  num: number;
  inMonth: boolean;
  isToday: boolean;
  items: CalendarItem[];
}

/**
 * Builds the 35 cells of the July 2026 month grid.
 *
 * Returns:
 *   Cells with day numbers, in-month/today flags, and each day's items
 *   (July 1, 2026 sits at cell index 3; today is July 16).
 */
function buildCells(): CalendarCell[] {
  const cells: CalendarCell[] = [];
  for (let cellIndex = 0; cellIndex < 35; cellIndex++) {
    const dayNum = cellIndex - 2;
    const inMonth = dayNum >= 1 && dayNum <= 31;
    const num = inMonth ? dayNum : dayNum < 1 ? 28 + cellIndex : dayNum - 31;
    cells.push({
      num,
      inMonth,
      isToday: dayNum === 16,
      items: inMonth
        ? CALENDAR_ITEMS.filter((item) => item.day === dayNum)
        : [],
    });
  }
  return cells;
}

/**
 * Resolves a campaign name to its workspace route.
 *
 * Args:
 *   name: A campaign display name from the calendar fixtures.
 *
 * Returns:
 *   The workspace route, or the campaigns list as a fallback.
 */
function campaignHref(name: string): string {
  const slug = campaignSlugForName(name);
  return slug ? `/campaigns/${slug}` : "/campaigns";
}

/** Renders the Calendar / List / By-campaign segmented toggle. */
function ModeToggle() {
  const calMode = useDemoStore((state) => state.calMode);
  const setCalMode = useDemoStore((state) => state.setCalMode);

  return (
    <div className="flex gap-0.5 rounded-[9px] bg-slate-100 p-[3px]">
      {MODES.map((mode) => (
        <button
          key={mode.key}
          onClick={() => setCalMode(mode.key)}
          aria-pressed={calMode === mode.key}
          className={cn(
            "cursor-pointer rounded-[7px] px-3 py-[5px] text-[12.5px] font-semibold",
            calMode === mode.key
              ? "bg-card text-foreground shadow-sm"
              : "text-muted-foreground",
          )}
        >
          {mode.label}
        </button>
      ))}
    </div>
  );
}

/** Renders the July 2026 month grid with the item-detail side panel. */
function MonthGrid() {
  const calSelIdx = useDemoStore((state) => state.calSelIdx);
  const setCalSelIdx = useDemoStore((state) => state.setCalSelIdx);
  const selected = CALENDAR_ITEMS[calSelIdx] ?? CALENDAR_ITEMS[0];

  const fields = [
    { k: "Campaign", v: selected.campaign },
    { k: "Audience", v: selected.audience },
    { k: "Funnel objective", v: selected.funnel },
    { k: "Channel", v: selected.channel },
    { k: "Content pillar", v: selected.pillar },
    { k: "Scheduled", v: `Jul ${selected.day}, 2026` },
  ];

  return (
    <div className="flex max-w-[1120px] flex-col items-start gap-5 lg:flex-row">
      <div className="w-full min-w-0 overflow-x-auto lg:flex-1">
        <Card className="min-w-[640px]">
          <div className="grid grid-cols-7 border-b">
            {DOWS.map((dow) => (
              <div
                key={dow}
                className="px-2.5 py-2 text-[11px] font-bold tracking-wide text-muted-foreground uppercase"
              >
                {dow}
              </div>
            ))}
          </div>
          <div className="grid grid-cols-7">
            {buildCells().map((cell, index) => (
              <div
                key={index}
                className={cn(
                  "min-h-[86px] min-w-0 overflow-hidden border-r border-b border-slate-100 p-1.5",
                  cell.inMonth ? "bg-card" : "bg-slate-50",
                )}
              >
                <div
                  className={cn(
                    "flex size-5 items-center justify-center rounded-full text-[11.5px] font-semibold",
                    cell.isToday
                      ? "bg-primary text-primary-foreground"
                      : cell.inMonth
                        ? "text-slate-700"
                        : "text-slate-300",
                  )}
                >
                  {cell.num}
                </div>
                <div className="mt-[3px] flex flex-col gap-[3px]">
                  {cell.items.map((item) => (
                    <button
                      key={item.title}
                      onClick={() => setCalSelIdx(CALENDAR_ITEMS.indexOf(item))}
                      className={cn(
                        "min-w-0 max-w-full cursor-pointer truncate rounded-md border-l-[3px] px-[7px] py-[3px] text-left text-[11px] font-semibold hover:brightness-[0.96]",
                        statusPillClasses(item.status),
                        statusEdgeClass(item.status),
                      )}
                    >
                      {shortTitle(item.title)}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
      <Card className="w-full shrink-0 px-[18px] py-4 lg:w-[296px]">
        <StatusPill status={selected.status} />
        <div className="mt-2 text-[15px] font-bold">{selected.title}</div>
        <div className="mt-2.5 flex flex-col">
          {fields.map((field) => (
            <div
              key={field.k}
              className="flex justify-between gap-2.5 border-b border-slate-100 py-[7px] text-[12.5px]"
            >
              <span className="text-muted-foreground">{field.k}</span>
              <span className="text-right font-semibold">{field.v}</span>
            </div>
          ))}
        </div>
        {selected.perf && (
          <div className="mt-3 rounded-[9px] border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-800">
            <strong>After publishing:</strong> {selected.perf}
          </div>
        )}
        <Link
          href={campaignHref(selected.campaign)}
          className="mt-3 block w-full rounded-lg border bg-card py-[7px] text-center text-[12.5px] font-semibold text-primary hover:border-indigo-200 hover:bg-indigo-50"
        >
          Open in campaign →
        </Link>
      </Card>
    </div>
  );
}

const LIST_GRID = "grid-cols-[0.7fr_2fr_1.2fr_1fr_1fr_1.1fr_1.2fr]";

/** Renders every calendar item as a metadata table row. */
function ListMode() {
  return (
    <div className="max-w-[1120px] overflow-x-auto">
      <Card className="min-w-[860px]">
        <div
          className={`grid ${LIST_GRID} gap-3 border-b px-[18px] py-2.5 text-[11px] font-bold tracking-wide text-muted-foreground uppercase`}
        >
          <div>Date</div>
          <div>Content</div>
          <div>Campaign</div>
          <div>Channel</div>
          <div>Funnel</div>
          <div>Status</div>
          <div>Performance</div>
        </div>
        {CALENDAR_ITEMS.map((item) => (
          <div
            key={item.title}
            className={`grid ${LIST_GRID} items-center gap-3 border-b border-slate-100 px-[18px] py-3 text-[13px] hover:bg-slate-50`}
          >
            <div className="font-semibold">Jul {item.day}</div>
            <div>
              <div className="font-semibold">{shortTitle(item.title)}</div>
              <div className="text-[11.5px] text-muted-foreground">
                {item.pillar} · {item.audience}
              </div>
            </div>
            <div className="text-[12.5px] text-slate-700">{item.campaign}</div>
            <div className="text-[12.5px] text-slate-700">{item.channel}</div>
            <div className="text-[12.5px] text-slate-700">{item.funnel}</div>
            <div>
              <StatusPill status={item.status} />
            </div>
            <div className="text-xs text-muted-foreground">
              {item.perf || "—"}
            </div>
          </div>
        ))}
      </Card>
    </div>
  );
}

/** Renders calendar items grouped under their campaigns with counts. */
function ByCampaignMode() {
  const groups = [...new Set(CALENDAR_ITEMS.map((item) => item.campaign))];

  return (
    <div className="flex max-w-[1120px] flex-col gap-4">
      {groups.map((name) => {
        const rows = CALENDAR_ITEMS.filter((item) => item.campaign === name);
        return (
          <Card key={name}>
            <div className="flex items-center justify-between border-b px-[18px] py-3">
              <span className="font-bold">{name}</span>
              <span className="text-xs text-muted-foreground">
                {rows.length} items
              </span>
            </div>
            {rows.map((item) => (
              <div
                key={item.title}
                className="flex items-center gap-3.5 border-b border-slate-100 px-[18px] py-[11px] text-[13px]"
              >
                <span className="w-[52px] font-semibold">Jul {item.day}</span>
                <span className="flex-1 font-semibold">
                  {shortTitle(item.title)}
                </span>
                <span className="text-[12.5px] text-muted-foreground">
                  {item.channel}
                </span>
                <StatusPill status={item.status} />
              </div>
            ))}
          </Card>
        );
      })}
    </div>
  );
}

/** Renders the content calendar in the mode selected in the store. */
export default function CalendarPage() {
  const calMode = useDemoStore((state) => state.calMode);

  return (
    <main className="flex-1 overflow-y-auto px-4 py-6 md:px-8 md:py-7">
      <div className="mb-[18px] flex max-w-[1120px] flex-wrap items-center justify-between gap-3">
        <h1 className="text-[22px] font-bold tracking-tight">
          Content · July 2026
        </h1>
        <ModeToggle />
      </div>
      {calMode === "calendar" && <MonthGrid />}
      {calMode === "list" && <ListMode />}
      {calMode === "campaign" && <ByCampaignMode />}
    </main>
  );
}

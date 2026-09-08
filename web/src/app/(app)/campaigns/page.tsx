"use client";

import { useEffect, useState, useTransition } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { Card } from "@/components/ui/card";
import { StatusPill } from "@/components/ui/status-pill";
import { toCampaignRow, type CampaignRowView } from "@/lib/campaigns";
import type { CampaignSummary } from "@/lib/engine";

import { archiveCampaignAction, loadCampaigns } from "./actions";

const ROW_GRID = "grid-cols-[2.2fr_1.2fr_1.3fr_2fr_auto]";

/** Renders the campaign portfolio table from the tenant's real campaigns. */
export default function CampaignsPage() {
  const router = useRouter();
  const [campaigns, setCampaigns] = useState<CampaignSummary[] | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [, startTransition] = useTransition();

  const refresh = () =>
    loadCampaigns()
      .then(setCampaigns)
      .catch(() => {
        setCampaigns([]);
        setFailure("We could not load your campaigns. Refresh to try again.");
      });

  useEffect(() => {
    void refresh();
  }, []);

  const archive = (slug: string) =>
    startTransition(() => {
      void archiveCampaignAction(slug).then(refresh);
    });

  const rows: CampaignRowView[] = (campaigns ?? []).map(toCampaignRow);

  return (
    <main className="flex-1 overflow-y-auto px-4 py-6 md:px-8 md:py-7">
      <div className="mb-[18px] flex max-w-[1120px] items-center justify-between">
        <h1 className="text-[22px] font-bold tracking-tight">Campaigns</h1>
        <Link
          href="/campaigns/new"
          className="rounded-lg bg-primary px-3.5 py-2 text-[13px] font-semibold text-primary-foreground hover:bg-indigo-700"
        >
          New campaign
        </Link>
      </div>
      {failure && (
        <div className="mb-3 max-w-[1120px] rounded-[10px] border border-red-200 bg-red-50 px-3.5 py-2.5 text-[12.5px] text-red-700">
          {failure}
        </div>
      )}
      <div className="max-w-[1120px] overflow-x-auto">
        <Card className="min-w-[760px]">
          <div
            className={`grid ${ROW_GRID} gap-3 border-b px-[18px] py-2.5 text-[11px] font-bold tracking-wide text-muted-foreground uppercase`}
          >
            <div>Campaign</div>
            <div>Stage</div>
            <div>Status</div>
            <div>Next action</div>
            <div />
          </div>
          {campaigns === null && (
            <div className="px-[18px] py-6 text-[13px] text-muted-foreground">
              Loading your campaigns…
            </div>
          )}
          {campaigns !== null && rows.length === 0 && (
            <div className="px-[18px] py-6 text-[13px] text-muted-foreground">
              No campaigns yet. Create one and we will run it through research,
              strategy and planning.
            </div>
          )}
          {rows.map((row) => (
            <div
              key={row.slug}
              role="link"
              tabIndex={0}
              onClick={() => router.push(`/campaigns/${row.slug}`)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  router.push(`/campaigns/${row.slug}`);
                }
              }}
              className={`grid ${ROW_GRID} cursor-pointer items-center gap-3 border-b border-slate-100 px-[18px] py-3.5 hover:bg-slate-50`}
            >
              <div>
                <div className="font-semibold">{row.name}</div>
                <div className="text-xs text-muted-foreground">
                  {row.objective}
                </div>
              </div>
              <div className="text-[13px]">
                {row.stage}{" "}
                <span className="text-xs text-slate-400">{row.stageNum}</span>
              </div>
              <div>
                <StatusPill status={row.status} />
              </div>
              <div className="text-[13px] text-slate-700">{row.next}</div>
              <button
                type="button"
                aria-label={`Archive ${row.name}`}
                onClick={(event) => {
                  event.stopPropagation();
                  archive(row.slug);
                }}
                className="cursor-pointer rounded-lg border bg-card px-2.5 py-1 text-xs font-semibold hover:bg-slate-50"
              >
                Archive
              </button>
            </div>
          ))}
        </Card>
      </div>
    </main>
  );
}

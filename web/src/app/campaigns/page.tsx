"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { Card } from "@/components/ui/card";
import { StatusPill } from "@/components/ui/status-pill";
import { createdCampaignToRow } from "@/lib/campaigns";
import { campaignRows } from "@/lib/mock-data";
import { useDemoStore } from "@/lib/store";

const ROW_GRID = "grid-cols-[2.2fr_1.2fr_1.3fr_2fr_0.8fr]";

/** Renders the campaign portfolio table with the New-campaign action. */
export default function CampaignsPage() {
  const approved = useDemoStore((state) => state.approved);
  const createdCampaigns = useDemoStore((state) => state.createdCampaigns);
  const router = useRouter();
  const rows = [
    ...campaignRows(approved),
    ...createdCampaigns.map(createdCampaignToRow),
  ];

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
      <div className="max-w-[1120px] overflow-x-auto">
        <Card className="min-w-[760px]">
          <div
            className={`grid ${ROW_GRID} gap-3 border-b px-[18px] py-2.5 text-[11px] font-bold tracking-wide text-muted-foreground uppercase`}
          >
            <div>Campaign</div>
            <div>Stage</div>
            <div>Status</div>
            <div>Next action</div>
            <div>Updated</div>
          </div>
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
              <div className="text-xs text-muted-foreground">{row.updated}</div>
            </div>
          ))}
        </Card>
      </div>
    </main>
  );
}

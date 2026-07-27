import { Card } from "@/components/ui/card";
import { StatCard } from "@/components/ui/stat-card";
import { PERF_BIG, PERF_CHANGE, PERF_KEEP, PERF_WHY } from "@/lib/mock-data";

/**
 * Renders an uppercase section label.
 *
 * Args:
 *   children: The label text.
 *   tone: "primary" (indigo) or "positive" (emerald).
 */
function SectionLabel({
  children,
  tone = "primary",
}: {
  children: React.ReactNode;
  tone?: "primary" | "positive";
}) {
  return (
    <div
      className={
        tone === "primary"
          ? "text-[11px] font-bold tracking-wider text-primary uppercase"
          : "text-[11px] font-bold tracking-wider text-emerald-700 uppercase"
      }
    >
      {children}
    </div>
  );
}

/** Renders the Performance screen: headline metrics and narratives. */
export default function PerformancePage() {
  return (
    <main className="flex-1 overflow-y-auto px-4 py-6 md:px-8 md:py-7">
      <div className="max-w-[880px]">
        <div className="mb-[18px] flex items-center justify-between">
          <h1 className="text-[22px] font-bold tracking-tight">Performance</h1>
          <div className="flex gap-0.5 rounded-[9px] bg-slate-100 p-[3px] text-[12.5px] font-semibold">
            <span className="rounded-[7px] bg-card px-3 py-[5px] shadow-sm">
              28 days
            </span>
            <span className="px-3 py-[5px] text-muted-foreground">Quarter</span>
          </div>
        </div>

        <Card className="mb-4 px-[22px] py-[18px]">
          <SectionLabel>What happened</SectionLabel>
          <div className="my-3 grid grid-cols-2 gap-4 md:grid-cols-4">
            {PERF_BIG.map((stat) => (
              <StatCard
                key={stat.label}
                size="lg"
                label={stat.label}
                value={stat.value}
                delta={stat.delta}
              />
            ))}
          </div>
          <p className="border-t border-slate-100 pt-3 text-[13.5px] text-slate-700">
            Reach and repeat purchases grew while spend held flat. Instagram
            engagement dipped mid-month when static posts replaced the
            demo-video format for a week.
          </p>
        </Card>

        <Card className="mb-4 px-[22px] py-[18px]">
          <SectionLabel>Why it happened</SectionLabel>
          <div className="mt-2.5 flex flex-col gap-3">
            {PERF_WHY.map((why) => (
              <div
                key={why.title}
                className="flex flex-wrap gap-3 border-b border-slate-100 pb-3"
              >
                <div className="min-w-[240px] flex-1">
                  <div className="text-[13.5px] font-semibold">{why.title}</div>
                  <div className="mt-0.5 text-[12.5px] text-muted-foreground">
                    {why.body}
                  </div>
                </div>
                <div className="flex shrink-0 items-start gap-[5px]">
                  <span className="rounded-[5px] bg-slate-100 px-[7px] py-0.5 text-[10.5px] font-semibold whitespace-nowrap text-slate-600">
                    {why.link1}
                  </span>
                  <span className="rounded-[5px] bg-slate-100 px-[7px] py-0.5 text-[10.5px] font-semibold whitespace-nowrap text-slate-600">
                    {why.link2}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </Card>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-[1.4fr_1fr]">
          <Card className="px-[22px] py-[18px]">
            <SectionLabel>What should change</SectionLabel>
            <div className="mt-2.5 flex flex-col gap-2.5">
              {PERF_CHANGE.map((item) => (
                <div
                  key={item.title}
                  className="rounded-[10px] border px-3.5 py-3"
                >
                  <div className="text-[13.5px] font-semibold">
                    {item.title}
                  </div>
                  <div className="mt-0.5 text-[12.5px] text-muted-foreground">
                    {item.body}
                  </div>
                  <div className="mt-[9px] flex gap-2">
                    <button className="cursor-pointer rounded-[7px] bg-primary px-[11px] py-[5px] text-xs font-semibold text-primary-foreground hover:bg-indigo-700">
                      Apply to plan
                    </button>
                    <button className="cursor-pointer rounded-[7px] border bg-card px-[11px] py-[5px] text-xs font-semibold text-muted-foreground hover:bg-slate-50">
                      Dismiss
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </Card>
          <Card className="self-start px-[22px] py-[18px]">
            <SectionLabel tone="positive">Keep unchanged</SectionLabel>
            <div className="mt-2.5 flex flex-col gap-2.5 text-[13px]">
              {PERF_KEEP.map((item) => (
                <div key={item.title} className="flex gap-2">
                  <span className="text-emerald-500">✓</span>
                  <div>
                    <strong>{item.title}</strong>
                    <div className="text-xs text-muted-foreground">
                      {item.body}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </main>
  );
}

"use client";

import { brandSectionsWithOnboarding } from "@/lib/onboarding";
import { useDemoStore } from "@/lib/store";
import { cn } from "@/lib/utils";

/** Renders the Brand screen: section index plus the selected section. */
export default function BrandPage() {
  const brandIdx = useDemoStore((state) => state.brandIdx);
  const setBrandIdx = useDemoStore((state) => state.setBrandIdx);
  const questionnaire = useDemoStore((state) => state.questionnaire);
  const onboarding = useDemoStore((state) => state.onboarding);
  const sections = brandSectionsWithOnboarding(questionnaire, onboarding);
  const section = sections[brandIdx] ?? sections[0];

  return (
    <main className="flex min-w-0 flex-1 flex-col overflow-hidden lg:flex-row">
      <div className="shrink-0 border-b bg-card lg:w-[224px] lg:overflow-y-auto lg:border-r lg:border-b-0">
        <div className="px-4 pt-4 pb-1 text-[11px] font-bold tracking-wider text-slate-400 uppercase lg:px-5 lg:pt-5 lg:pb-2.5">
          Brand source of truth
        </div>
        <nav
          aria-label="Brand sections"
          className="scrollbar-none flex gap-1 overflow-x-auto px-2.5 pb-3 lg:flex-col lg:gap-0 lg:pb-5"
        >
          {sections.map((item, index) => (
            <button
              key={item.name}
              onClick={() => setBrandIdx(index)}
              className={cn(
                "block w-auto cursor-pointer rounded-lg px-2.5 py-[7px] text-left text-[13px] whitespace-nowrap lg:w-full lg:whitespace-normal",
                brandIdx === index
                  ? "bg-indigo-50 font-semibold text-primary"
                  : "font-medium text-slate-700 hover:bg-slate-100",
              )}
            >
              {item.name}
            </button>
          ))}
        </nav>
      </div>
      <div className="flex-1 overflow-y-auto px-4 py-6 md:px-8 md:py-7">
        <div className="max-w-[680px]">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h1 className="text-xl font-bold tracking-tight">{section.name}</h1>
            <div className="text-xs text-muted-foreground">
              Last verified {section.verified} · <a href="#">Edit</a>
            </div>
          </div>
          <p className="mt-1.5 mb-[18px] text-[13px] text-muted-foreground">
            {section.desc}
          </p>
          <div className="flex flex-col gap-3">
            {section.entries.map((entry) => (
              <div
                key={entry.k}
                className="rounded-xl border bg-card px-[18px] py-[15px]"
              >
                <div className="flex items-center gap-2">
                  <div className="text-[13.5px] font-bold">{entry.k}</div>
                  {entry.warn && (
                    <span className="rounded-[5px] bg-red-100 px-[7px] py-px text-[10.5px] font-bold text-red-700">
                      RESTRICTED
                    </span>
                  )}
                </div>
                <div className="mt-1 text-[13.5px] text-slate-700">
                  {entry.v}
                </div>
                {entry.note && (
                  <div className="mt-1.5 border-t border-slate-100 pt-1.5 text-xs text-muted-foreground">
                    {entry.note}
                  </div>
                )}
              </div>
            ))}
          </div>
          <div className="mt-4 rounded-xl border border-indigo-200 bg-indigo-50 px-4 py-[13px] text-[12.5px] text-indigo-900">
            Every generated asset is scored against this section — see the
            alignment scorecard on any deliverable before you approve it.
          </div>
        </div>
      </div>
    </main>
  );
}

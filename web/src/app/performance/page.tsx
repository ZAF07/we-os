import Link from "next/link";

import { Card, CardHeader } from "@/components/ui/card";
import { StatusPill } from "@/components/ui/status-pill";
import {
  headingNamesPart,
  isBullet,
  kpiTier,
  planPart,
  plainText,
  toSections,
  withoutTierLabel,
  type DeliverableSection,
  type KpiTierName,
  type PlanPart,
} from "@/lib/deliverable";
import { engineErrorMessage } from "@/lib/engine";

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
    return (
      <Shell>
        <p role="alert" className="text-[13px] text-muted-foreground">
          {engineErrorMessage(error)}
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
        className="flex flex-col gap-4 px-[18px] pb-4"
      >
        {toSections(plan.content).map((section, index) => (
          <PlanSection key={`${section.heading}-${index}`} section={section} />
        ))}
      </article>
    </Card>
  );
}

const PART_LABELS: Record<PlanPart, string> = {
  channels: "Channel mix",
  spend: "Spend allocation",
  placements: "Placements · format specs",
  kpis: "KPI targets · all three tiers",
};

const KPI_TIERS: readonly KpiTierName[] = ["Business", "Marketing", "Creative"];

/**
 * Renders one section of a plan, with the treatment its part deserves.
 *
 * The screen is a reader, not a check: identifying a section lets it say which
 * of the plan's four parts it is showing instead of laying them all out alike.
 * A heading it does not recognise is not a problem to report — it renders the
 * way every section did before, since whether the plan is complete was settled
 * upstream by the guardrail and the reviewer that scores against it.
 *
 * Args:
 *   section: One heading and the lines the specialist wrote beneath it.
 */
function PlanSection({ section }: { section: DeliverableSection }) {
  const part = planPart(section.heading);

  return (
    <section aria-label={part ? PART_LABELS[part] : undefined}>
      {section.heading !== "" && (
        <SectionHeading heading={section.heading} part={part} />
      )}
      {part === "kpis" ? (
        <KpiTiers lines={section.lines} />
      ) : part === "placements" ? (
        <PlacementSpecs lines={section.lines} />
      ) : (
        <PlainLines lines={section.lines} emphasised={part === "spend"} />
      )}
    </section>
  );
}

/**
 * Renders a section's heading, naming the part when the heading is one.
 *
 * Args:
 *   heading: The heading as the specialist wrote it.
 *   part: The plan part it names, or null when it names none.
 */
function SectionHeading({
  heading,
  part,
}: {
  heading: string;
  part: PlanPart | null;
}) {
  return (
    <h3 className="mb-1.5 flex items-baseline gap-2 text-[11px] font-bold tracking-wide text-muted-foreground uppercase">
      <span className={part ? "text-slate-700" : undefined}>{heading}</span>
      {part && !headingNamesPart(heading, part) && (
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold tracking-normal text-slate-600 normal-case">
          {PART_LABELS[part]}
        </span>
      )}
    </h3>
  );
}

/**
 * Renders the KPI section grouped by the three tiers a campaign must define.
 *
 * Lines that name no tier keep their place beneath the grouped ones rather than
 * being dropped — the specialist wrote them, and the screen shows what is there.
 *
 * A tier with no line under this heading gets no card. Rendering an empty slot
 * would make a plan missing a tier look visibly incomplete, and that is the
 * guardrail's judgement to make, not this screen's — the screen reports a plan
 * the reviewer has already scored.
 *
 * Args:
 *   lines: The KPI section's lines.
 */
function KpiTiers({ lines }: { lines: string[] }) {
  const grouped = KPI_TIERS.map((tier) => ({
    tier,
    stated: lines.filter((line) => kpiTier(line) === tier),
  })).filter((group) => group.stated.length > 0);

  const ungrouped = lines.filter((line) => kpiTier(line) === null);

  return (
    <div className="flex flex-col gap-2">
      {grouped.length > 0 && (
        <div className="grid gap-2 sm:grid-cols-3">
          {grouped.map(({ tier, stated }) => (
            <div key={tier} className="rounded-[10px] border bg-card px-3 py-2">
              <div className="text-[10.5px] font-bold tracking-wide text-muted-foreground uppercase">
                {tier}
              </div>
              {stated.map((line, position) => (
                <div
                  key={position}
                  className="mt-0.5 text-[13px] text-slate-800"
                >
                  {withoutTierLabel(line, tier)}
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
      <PlainLines lines={ungrouped} emphasised={false} />
    </div>
  );
}

/**
 * Renders the placements section as the specs creative has to satisfy.
 *
 * Each bullet is laid out as its own spec row — the plan writes one per
 * placement, and reading them side by side is what makes them usable by whoever
 * builds the creative. No spec is parsed out of the prose; the screen shows the
 * line the specialist wrote, in a place that says what it is.
 *
 * Args:
 *   lines: The placements section's lines.
 */
function PlacementSpecs({ lines }: { lines: string[] }) {
  const specs = lines.filter(isBullet);
  const prose = lines.filter((line) => !isBullet(line));

  if (specs.length === 0)
    return <PlainLines lines={lines} emphasised={false} />;

  return (
    <div className="flex flex-col gap-2">
      <PlainLines lines={prose} emphasised={false} />
      <ul className="grid gap-1.5 sm:grid-cols-2">
        {specs.map((line, position) => (
          <li
            key={position}
            className="rounded-[10px] border bg-card px-3 py-2 text-[13px] text-slate-800"
          >
            {plainText(line)}
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * Renders a section's lines the way every section rendered before this screen
 * identified any of them — bullets as a list, prose as paragraphs.
 *
 * Args:
 *   lines: The section's lines.
 *   emphasised: Whether to give the lines the weight the spend allocation wants,
 *     it being the decision a reader scans for first.
 */
function PlainLines({
  lines,
  emphasised,
}: {
  lines: string[];
  emphasised: boolean;
}) {
  if (lines.length === 0) return null;

  const text = emphasised
    ? "text-[14px] font-semibold text-slate-900"
    : "text-[13.5px] text-slate-800";

  if (lines.every(isBullet)) {
    return (
      <ul className="flex flex-col gap-1">
        {lines.map((line, position) => (
          <li key={position} className={`flex gap-2 ${text}`}>
            <span className="text-primary">·</span>
            <span>{plainText(line)}</span>
          </li>
        ))}
      </ul>
    );
  }

  return (
    <>
      {lines.map((line, position) => (
        <p key={position} className={`leading-relaxed ${text}`}>
          {plainText(line)}
        </p>
      ))}
    </>
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

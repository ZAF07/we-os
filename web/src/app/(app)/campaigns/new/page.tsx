"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useWizard } from "@/components/wizard/use-wizard";
import { Field, WizardShell } from "@/components/wizard/wizard";
import type { AudienceSegment, CampaignGoalInput } from "@/lib/engine";
import { useSessionReady } from "@/lib/use-session-ready";
import { cn } from "@/lib/utils";

import { createCampaignAction, loadAudienceSegments } from "../actions";

/**
 * The wizard collects exactly the campaign goal the DNA Gate requires — no
 * more. It does not ask which channels to run on: that is the performance
 * specialist's decision at stage 4, which the pipeline places before creative
 * precisely so the system makes the call (ADR-0016).
 */
const STEPS = ["Campaign", "Objective", "Audience & budget", "Review"];

const CURRENCIES = ["SGD", "AUD", "USD", "EUR", "GBP"];

interface Draft {
  name: string;
  objective: string;
  audience_segment: string;
  amount: string;
  currency: string;
  start: string;
  end: string;
  business: string;
  marketing: string;
  creative: string;
  offer: string;
}

const EMPTY: Draft = {
  name: "",
  objective: "",
  audience_segment: "",
  amount: "",
  currency: CURRENCIES[0],
  start: "",
  end: "",
  business: "",
  marketing: "",
  creative: "",
  offer: "",
};

/** The Required draft fields for each step, in the order they are asked. */
const REQUIRED_BY_STEP: Array<Array<keyof Draft>> = [
  ["name", "objective"],
  ["business", "marketing", "creative"],
  ["audience_segment", "amount", "currency", "start", "end"],
  [],
];

/**
 * Converts the wizard draft into the goal the engine takes.
 *
 * Args:
 *   draft: The answers entered in the wizard.
 *
 * Returns:
 *   The campaign goal payload.
 */
function toGoal(draft: Draft): CampaignGoalInput {
  return {
    name: draft.name.trim(),
    objective: draft.objective.trim(),
    timeframe: { start_date: draft.start, end_date: draft.end },
    budget: { amount: Number(draft.amount), currency: draft.currency },
    audience_segment: draft.audience_segment,
    kpis: {
      business: draft.business.trim(),
      marketing: draft.marketing.trim(),
      creative: draft.creative.trim(),
    },
    offer: draft.offer.trim(),
  };
}

/**
 * Renders the new-campaign wizard, which creates a real campaign.
 *
 * The goal is submitted once at the end rather than saved step by step, so
 * the wizard's per-transition save has nothing to write and every transition
 * is free to proceed.
 *
 * Returns:
 *   The wizard page element.
 */
export default function NewCampaignPage() {
  const router = useRouter();
  const [draft, setDraft] = useState<Draft>(EMPTY);
  const [segments, setSegments] = useState<AudienceSegment[] | null>(null);
  const [segmentsFailed, setSegmentsFailed] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const startSegmentLoad = useCallback(() => {
    let abandoned = false;
    void (async () => {
      try {
        const loaded = await loadAudienceSegments();
        if (!abandoned) setSegments(loaded);
      } catch {
        // Retried once before anything is said to the owner: the failure this
        // recovers from is transient latency, and a second attempt costs less
        // than making someone read an error and click a button for a blip.
        try {
          const loaded = await loadAudienceSegments();
          if (!abandoned) setSegments(loaded);
        } catch {
          if (!abandoned) setSegmentsFailed(true);
        }
      }
    })();
    // Returned so a load whose answer nobody is waiting for any more cannot
    // land on the field: the effect below abandons it when the page goes away,
    // and `retrySegments` abandons it when a retry supersedes it.
    return () => {
      abandoned = true;
    };
  }, []);

  // Not before the session is ready to be used: the load is a server action,
  // which the middleware cannot renew, so on a page opened cold it must wait
  // for the browser script to refresh the token. A page whose script has
  // already loaded waits for nothing and loads in its first render, as before.
  const sessionReady = useSessionReady();
  useEffect(() => {
    if (!sessionReady) return;
    return startSegmentLoad();
  }, [sessionReady, startSegmentLoad]);

  const abandonSegmentLoad = useRef<(() => void) | null>(null);

  /**
   * Puts the field back into its loading state and asks for the segments again.
   *
   * The load in flight is abandoned first, so an earlier attempt answering late
   * cannot overwrite the answer this one is about to give.
   */
  const retrySegments = () => {
    abandonSegmentLoad.current?.();
    setSegments(null);
    setSegmentsFailed(false);
    abandonSegmentLoad.current = startSegmentLoad();
  };

  const setField = (field: keyof Draft) => (value: string) =>
    setDraft((previous) => ({ ...previous, [field]: value }));

  const missing = (field: keyof Draft) => !draft[field].trim();

  const stepIncomplete = (step: number) => REQUIRED_BY_STEP[step].some(missing);

  const { step, attempted, busy, back, next } = useWizard({
    stepCount: STEPS.length,
    isStepIncomplete: stepIncomplete,
    save: async () => true,
    onFinish: () => {
      setSubmitting(true);
      void createCampaignAction(toGoal(draft)).then(({ campaign, error }) => {
        setSubmitting(false);
        if (campaign) {
          router.push(`/campaigns/${campaign.id}`);
          return;
        }
        setFailure(error);
      });
    },
  });

  const showError = (field: keyof Draft) => attempted && missing(field);

  const text = (field: keyof Draft) => ({
    id: field,
    value: draft[field],
    onChange: (
      event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
    ) => setField(field)(event.target.value),
  });

  const review: Array<[string, string]> = [
    ["Campaign", draft.name],
    ["Business objective", draft.objective],
    ["Business KPI", draft.business],
    ["Marketing KPI", draft.marketing],
    ["Creative KPI", draft.creative],
    ["Audience segment", draft.audience_segment],
    ["Budget", `${draft.amount} ${draft.currency}`],
    ["Timeframe", `${draft.start} → ${draft.end}`],
    ["Offer", draft.offer || "—"],
  ];

  return (
    <WizardShell
      title="New campaign"
      subtitle="The goal a campaign needs before any strategy work can start. We choose the channels later — that is our job, not yours."
      steps={STEPS}
      current={step}
      error={
        failure ??
        (attempted && stepIncomplete(step)
          ? "Fill in the required fields to continue."
          : undefined)
      }
      nextLabel={submitting ? "Creating…" : "Create campaign"}
      busy={busy || submitting}
      onBack={back}
      onNext={next}
    >
      {step === 0 && (
        <>
          <Field
            label="Campaign name"
            htmlFor="name"
            required
            error={showError("name")}
          >
            <Input {...text("name")} placeholder="Autumn Referral Push" />
          </Field>
          <Field
            label="Primary business objective"
            htmlFor="objective"
            required
            error={showError("objective")}
            hint="One measurable outcome — the revenue result this campaign is for."
          >
            <Textarea
              {...text("objective")}
              placeholder="120 refill subscriptions in 8 weeks"
            />
          </Field>
        </>
      )}

      {step === 1 && (
        <>
          <div className="text-[12.5px] text-muted-foreground">
            Every campaign defines all three tiers. Without them there is no
            definition of success to optimise against.
          </div>
          <Field
            label="Business KPI"
            htmlFor="business"
            required
            error={showError("business")}
            hint="Revenue, leads, bookings, sales or retention."
          >
            <Input
              {...text("business")}
              placeholder="120 refill subscriptions"
            />
          </Field>
          <Field
            label="Marketing KPI"
            htmlFor="marketing"
            required
            error={showError("marketing")}
            hint="CTR, CPC, CPM or conversion rate."
          >
            <Input
              {...text("marketing")}
              placeholder="2.5% landing-page conversion"
            />
          </Field>
          <Field
            label="Creative KPI"
            htmlFor="creative"
            required
            error={showError("creative")}
            hint="Hook rate, watch time or engagement rate."
          >
            <Input
              {...text("creative")}
              placeholder="30% hook rate on the launch video"
            />
          </Field>
        </>
      )}

      {step === 2 && (
        <>
          <Field
            label="Target audience segment"
            htmlFor="audience_segment"
            required
            error={showError("audience_segment")}
            hint="From the segments you described in your Brand DNA — a campaign targets one group, never everyone."
          >
            {segmentsFailed ? (
              <div className="text-[13px] text-muted-foreground">
                We could not load your audience segments — this is on us, not on
                your Brand DNA.{" "}
                <button
                  type="button"
                  onClick={retrySegments}
                  className="font-semibold text-slate-800 underline underline-offset-2"
                >
                  Try again
                </button>
              </div>
            ) : segments === null ? (
              <div className="text-[13px] text-muted-foreground">
                Loading your segments…
              </div>
            ) : segments.length === 0 ? (
              <div className="text-[13px] text-muted-foreground">
                Your Brand DNA names no audience segments yet. Complete
                onboarding first.
              </div>
            ) : (
              <div className="flex flex-col gap-1.5" role="radiogroup">
                {segments.map((segment) => {
                  const chosen = draft.audience_segment === segment.title;
                  return (
                    <button
                      key={segment.title}
                      type="button"
                      role="radio"
                      aria-checked={chosen}
                      onClick={() =>
                        setField("audience_segment")(segment.title)
                      }
                      className={cn(
                        "cursor-pointer rounded-lg border px-3 py-2 text-left text-[13px]",
                        chosen
                          ? "border-primary bg-indigo-50 text-primary"
                          : "bg-card hover:border-indigo-200",
                      )}
                    >
                      <span
                        className={cn(
                          "block",
                          chosen ? "font-semibold" : "font-medium",
                        )}
                      >
                        {segment.title}
                      </span>
                      {segment.description !== "" && (
                        <span className="mt-0.5 block text-[12.5px] font-normal text-muted-foreground">
                          {segment.description}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            )}
          </Field>
          <div className="grid grid-cols-[2fr_1fr] gap-4">
            <Field
              label="Campaign budget"
              htmlFor="amount"
              required
              error={showError("amount")}
              hint="The media spend available to this campaign."
            >
              <Input
                {...text("amount")}
                type="number"
                min="0"
                placeholder="4000"
              />
            </Field>
            <Field
              label="Currency"
              htmlFor="currency"
              required
              error={showError("currency")}
            >
              <select
                id="currency"
                value={draft.currency}
                onChange={(event) => setField("currency")(event.target.value)}
                className="h-9 w-full rounded-md border bg-card px-3 text-[13px]"
              >
                {CURRENCIES.map((code) => (
                  <option key={code} value={code}>
                    {code}
                  </option>
                ))}
              </select>
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Field
              label="Start date"
              htmlFor="start"
              required
              error={showError("start")}
            >
              <Input type="date" {...text("start")} />
            </Field>
            <Field
              label="End date"
              htmlFor="end"
              required
              error={showError("end")}
            >
              <Input type="date" {...text("end")} />
            </Field>
          </div>
          <Field label="Offer or promotion" htmlFor="offer">
            <Input
              {...text("offer")}
              placeholder="Optional — a discount, bundle or launch hook"
            />
          </Field>
        </>
      )}

      {step === 3 && (
        <div>
          <div className="mb-2 text-[11px] font-bold tracking-wide text-muted-foreground uppercase">
            Review before creating
          </div>
          <div className="flex flex-col">
            {review.map(([label, value]) => (
              <div
                key={label}
                className="flex justify-between gap-2.5 border-b border-slate-100 py-[7px] text-[13px] last:border-b-0"
              >
                <span className="text-muted-foreground">{label}</span>
                <span className="text-right font-semibold">{value}</span>
              </div>
            ))}
          </div>
          <div className="mt-3 rounded-[10px] border border-indigo-200 bg-indigo-50 px-3.5 py-2.5 text-[12.5px] text-indigo-900">
            Creating the campaign opens its Workspace. Research and strategy run
            from there, and we choose the channels in the performance plan.
          </div>
        </div>
      )}
    </WizardShell>
  );
}

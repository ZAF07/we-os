"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useWizard } from "@/components/wizard/use-wizard";
import { Field, WizardShell } from "@/components/wizard/wizard";
import { slugify, type CreatedCampaign } from "@/lib/campaigns";
import { FIXTURE_CAMPAIGN_SLUGS } from "@/lib/mock-data";
import { audienceSegmentOptions } from "@/lib/onboarding";
import { useDemoStore } from "@/lib/store";
import { cn } from "@/lib/utils";

const STEPS = [
  "Request",
  "Objective",
  "Audience",
  "Offer & budget",
  "Channels",
  "Review",
];

const OBJECTIVES = [
  "Generate qualified leads",
  "Increase sales",
  "Launch a product",
  "Increase trial registrations",
  "Improve customer retention",
  "Build category awareness",
  "Re-engage inactive customers",
  "Promote an event",
];

const ACTIONS = [
  "Purchase",
  "Book a consultation",
  "Request a quotation",
  "Register",
  "Download",
  "Subscribe",
  "Start a trial",
  "Visit a location",
];

const FUNNEL_STAGES = ["Awareness", "Consideration", "Conversion", "Retention"];

const CHANNELS = [
  "Instagram",
  "Email",
  "Blog / SEO",
  "YouTube",
  "Paid social",
  "Landing page",
];

type Draft = Omit<CreatedCampaign, "slug">;

const EMPTY: Draft = {
  name: "",
  reason: "",
  owner: "",
  objective: "",
  action: "",
  metric: "",
  audience: "",
  funnel: "",
  offer: "",
  cta: "",
  budget: "",
  start: "",
  end: "",
  channels: [],
};

type DraftText = Exclude<keyof Draft, "channels">;

const REQUIRED_BY_STEP: DraftText[][] = [
  ["name", "reason", "owner"],
  ["objective", "action", "metric"],
  ["audience"],
  ["offer", "cta", "budget", "start", "end"],
  [],
  [],
];

/** Renders the multi-step new-campaign wizard. */
export default function NewCampaignPage() {
  const router = useRouter();
  const onboarding = useDemoStore((state) => state.onboarding);
  const createdCampaigns = useDemoStore((state) => state.createdCampaigns);
  const addCampaign = useDemoStore((state) => state.addCampaign);
  const [draft, setDraft] = useState<Draft>(EMPTY);

  const segments = audienceSegmentOptions(onboarding);

  const setField = (field: DraftText) => (value: string) =>
    setDraft((prev) => ({ ...prev, [field]: value }));

  const toggleChannel = (channel: string) =>
    setDraft((prev) => ({
      ...prev,
      channels: prev.channels.includes(channel)
        ? prev.channels.filter((existing) => existing !== channel)
        : [...prev.channels, channel],
    }));

  const missing = (field: DraftText) => !draft[field].trim();

  const stepIncomplete = (step: number) => {
    if (REQUIRED_BY_STEP[step].some(missing)) return true;
    if (step === 4 && draft.channels.length === 0) return true;
    return false;
  };

  const { step, attempted, back, next } = useWizard({
    stepCount: STEPS.length,
    isStepIncomplete: stepIncomplete,
    onFinish: () => {
      const taken = [
        ...FIXTURE_CAMPAIGN_SLUGS,
        ...createdCampaigns.map((campaign) => campaign.slug),
      ];
      const campaign: CreatedCampaign = {
        ...draft,
        slug: slugify(draft.name, taken),
      };
      addCampaign(campaign);
      router.push(`/campaigns/${campaign.slug}`);
    },
  });

  const showError = (field: DraftText) => attempted && missing(field);

  const text = (field: DraftText) => ({
    id: field,
    value: draft[field],
    onChange: (
      event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
    ) => setField(field)(event.target.value),
  });

  const selectField = (
    field: DraftText,
    label: string,
    options: string[],
    required: boolean,
  ) => (
    <Field
      label={label}
      htmlFor={field}
      required={required}
      error={required && showError(field)}
    >
      <Select value={draft[field]} onValueChange={setField(field)}>
        <SelectTrigger id={field} className="w-full">
          <SelectValue placeholder="Select…" />
        </SelectTrigger>
        <SelectContent>
          {options.map((option) => (
            <SelectItem key={option} value={option}>
              {option}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </Field>
  );

  const review: Array<[string, string]> = [
    ["Campaign", draft.name],
    ["Why now", draft.reason],
    ["Owner & approver", draft.owner],
    ["Primary objective", draft.objective],
    ["Desired action", draft.action],
    ["Success metric", draft.metric],
    [
      "Audience",
      draft.funnel ? `${draft.audience} · ${draft.funnel}` : draft.audience,
    ],
    ["Offer", draft.offer],
    ["Call to action", draft.cta],
    ["Budget", draft.budget],
    ["Timeline", `${draft.start} → ${draft.end}`],
    ["Channels", draft.channels.join(", ")],
  ];

  return (
    <WizardShell
      title="New campaign"
      subtitle="The minimum a campaign needs before strategy work can start."
      steps={STEPS}
      current={step}
      error={
        attempted && stepIncomplete(step)
          ? step === 4
            ? "Select at least one channel to continue."
            : "Fill in the required fields to continue."
          : undefined
      }
      nextLabel="Create campaign"
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
            label="What are we promoting, and why now?"
            htmlFor="reason"
            required
            error={showError("reason")}
          >
            <Textarea
              {...text("reason")}
              placeholder="The product, event or initiative, and the reason this campaign exists."
            />
          </Field>
          <Field
            label="Campaign owner & approver"
            htmlFor="owner"
            required
            error={showError("owner")}
          >
            <Input {...text("owner")} placeholder="Maya Chen" />
          </Field>
        </>
      )}

      {step === 1 && (
        <>
          {selectField(
            "objective",
            "Primary business objective",
            OBJECTIVES,
            true,
          )}
          {selectField("action", "Desired customer action", ACTIONS, true)}
          <Field
            label="Primary success metric"
            htmlFor="metric"
            required
            error={showError("metric")}
          >
            <Input
              {...text("metric")}
              placeholder="1,500 new refill subscriptions in Q3"
            />
          </Field>
        </>
      )}

      {step === 2 && (
        <>
          <Field
            label="Primary audience segment"
            htmlFor="audience"
            required
            error={showError("audience")}
            hint="Inherited from onboarding — pick a segment instead of retyping it."
          >
            <div className="flex flex-col gap-1.5" role="radiogroup">
              {segments.map((segment) => (
                <button
                  key={segment}
                  type="button"
                  role="radio"
                  aria-checked={draft.audience === segment}
                  onClick={() => setField("audience")(segment)}
                  className={cn(
                    "cursor-pointer rounded-lg border px-3 py-2 text-left text-[13px] font-medium",
                    draft.audience === segment
                      ? "border-primary bg-indigo-50 font-semibold text-primary"
                      : "bg-card hover:border-indigo-200",
                  )}
                >
                  {segment}
                </button>
              ))}
            </div>
          </Field>
          {selectField("funnel", "Funnel stage", FUNNEL_STAGES, false)}
        </>
      )}

      {step === 3 && (
        <>
          <Field
            label="Offer being promoted"
            htmlFor="offer"
            required
            error={showError("offer")}
          >
            <Input
              {...text("offer")}
              placeholder="Starter Set at $42 with first refill free"
            />
          </Field>
          <Field
            label="Primary call to action"
            htmlFor="cta"
            required
            error={showError("cta")}
          >
            <Input {...text("cta")} placeholder="Start your refill plan" />
          </Field>
          <Field
            label="Total budget"
            htmlFor="budget"
            required
            error={showError("budget")}
          >
            <Input {...text("budget")} placeholder="$48k across paid + owned" />
          </Field>
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
        </>
      )}

      {step === 4 && (
        <Field
          label="Channels"
          htmlFor="channel-0"
          required
          hint="Where this campaign is allowed to run — strategy refines the final mix."
        >
          <div className="flex flex-col gap-2">
            {CHANNELS.map((channel, index) => (
              <div key={channel} className="flex items-center gap-2.5">
                <Checkbox
                  id={`channel-${index}`}
                  checked={draft.channels.includes(channel)}
                  onCheckedChange={() => toggleChannel(channel)}
                />
                <Label
                  htmlFor={`channel-${index}`}
                  className="text-[13px] font-medium"
                >
                  {channel}
                </Label>
              </div>
            ))}
          </div>
        </Field>
      )}

      {step === 5 && (
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
            Creating the campaign opens its Workspace at the Brief stage —
            research and strategy run from there.
          </div>
        </div>
      )}
    </WizardShell>
  );
}

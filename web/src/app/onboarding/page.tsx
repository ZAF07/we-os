"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useWizard } from "@/components/wizard/use-wizard";
import { Field, WizardShell } from "@/components/wizard/wizard";
import type { OnboardingData } from "@/lib/onboarding";
import { useDemoStore } from "@/lib/store";

const STEPS = ["Business", "Customers", "Positioning", "Voice", "Compliance"];

const EMPTY: OnboardingData = {
  companyName: "",
  companyDescription: "",
  industry: "",
  products: "",
  website: "",
  segments: [
    { name: "", desc: "" },
    { name: "", desc: "" },
    { name: "", desc: "" },
  ],
  problems: "",
  valueProp: "",
  promise: "",
  differentiators: "",
  claims: "",
  competitors: "",
  avoid: "",
  personality: "",
  tone: "",
  writingStyle: "",
  prohibitedTerms: "",
  restricted: "",
  disclaimers: "",
};

type TextField = Exclude<keyof OnboardingData, "segments">;

const REQUIRED_BY_STEP: TextField[][] = [
  ["companyName", "companyDescription", "industry", "products"],
  ["problems"],
  ["valueProp", "promise", "differentiators"],
  ["personality", "tone"],
  ["restricted"],
];

/** Renders the multi-step company-onboarding wizard. */
export default function OnboardingPage() {
  const router = useRouter();
  const completeOnboarding = useDemoStore((state) => state.completeOnboarding);
  const setBrandIdx = useDemoStore((state) => state.setBrandIdx);
  const [data, setData] = useState<OnboardingData>(EMPTY);

  const setField = (field: TextField) => (value: string) =>
    setData((prev) => ({ ...prev, [field]: value }));

  const setSegment = (index: number, key: "name" | "desc", value: string) =>
    setData((prev) => ({
      ...prev,
      segments: prev.segments.map((segment, i) =>
        i === index ? { ...segment, [key]: value } : segment,
      ),
    }));

  const missing = (field: TextField) => !data[field].trim();
  const segmentMissing = (key: "name" | "desc") =>
    !data.segments[0][key].trim();

  const stepIncomplete = (step: number) => {
    if (REQUIRED_BY_STEP[step].some(missing)) return true;
    if (step === 1 && (segmentMissing("name") || segmentMissing("desc"))) {
      return true;
    }
    return false;
  };

  const { step, attempted, back, next } = useWizard({
    stepCount: STEPS.length,
    isStepIncomplete: stepIncomplete,
    onFinish: () => {
      completeOnboarding(data);
      setBrandIdx(0);
      router.push("/brand");
    },
  });

  const showError = (field: TextField) => attempted && missing(field);

  const text = (field: TextField) => ({
    id: field,
    value: data[field],
    onChange: (
      event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
    ) => setField(field)(event.target.value),
  });

  return (
    <WizardShell
      title="Set up your company"
      subtitle="The durable context every campaign is grounded in — reviewable any time on the Brand screen."
      note="AI extraction from your documents isn't available yet — enter the essentials manually."
      steps={STEPS}
      current={step}
      error={
        attempted && stepIncomplete(step)
          ? "Fill in the required fields to continue."
          : undefined
      }
      nextLabel="Finish onboarding"
      onBack={back}
      onNext={next}
    >
      {step === 0 && (
        <>
          <Field
            label="Company name"
            htmlFor="companyName"
            required
            error={showError("companyName")}
          >
            <Input {...text("companyName")} placeholder="Fernway" />
          </Field>
          <Field
            label="Company description"
            htmlFor="companyDescription"
            required
            error={showError("companyDescription")}
          >
            <Textarea
              {...text("companyDescription")}
              placeholder="What the business does, for whom, and how it makes money."
            />
          </Field>
          <Field
            label="Industry & category"
            htmlFor="industry"
            required
            error={showError("industry")}
          >
            <Input
              {...text("industry")}
              placeholder="Premium home care · refill subscriptions"
            />
          </Field>
          <Field
            label="Products or services"
            htmlFor="products"
            required
            error={showError("products")}
            hint="One per line: Name — description"
          >
            <Textarea
              {...text("products")}
              placeholder={"Starter Set — forever bottle + first 3 refills"}
            />
          </Field>
          <Field label="Website" htmlFor="website">
            <Input {...text("website")} placeholder="https://…" />
          </Field>
        </>
      )}

      {step === 1 && (
        <>
          <Field
            label="Primary customer segment"
            htmlFor="segment-0-name"
            required
            error={attempted && segmentMissing("name")}
          >
            <Input
              id="segment-0-name"
              value={data.segments[0].name}
              onChange={(event) => setSegment(0, "name", event.target.value)}
              placeholder="Low-waste households (28–45)"
            />
          </Field>
          <Field
            label="What defines them"
            htmlFor="segment-0-desc"
            required
            error={attempted && segmentMissing("desc")}
          >
            <Textarea
              id="segment-0-desc"
              value={data.segments[0].desc}
              onChange={(event) => setSegment(0, "desc", event.target.value)}
              placeholder="Practical, cost-aware, already buying eco."
            />
          </Field>
          {[1, 2].map((index) => (
            <Field
              key={index}
              label={`Segment ${index + 1} (optional)`}
              htmlFor={`segment-${index}-name`}
            >
              <div className="flex flex-col gap-1.5">
                <Input
                  id={`segment-${index}-name`}
                  value={data.segments[index].name}
                  onChange={(event) =>
                    setSegment(index, "name", event.target.value)
                  }
                  placeholder="Segment name"
                />
                <Input
                  id={`segment-${index}-desc`}
                  aria-label={`Segment ${index + 1} description`}
                  value={data.segments[index].desc}
                  onChange={(event) =>
                    setSegment(index, "desc", event.target.value)
                  }
                  placeholder="What defines them"
                />
              </div>
            </Field>
          ))}
          <Field
            label="Customer problems & pain points"
            htmlFor="problems"
            required
            error={showError("problems")}
          >
            <Textarea
              {...text("problems")}
              placeholder="What they struggle with today, in their words."
            />
          </Field>
        </>
      )}

      {step === 2 && (
        <>
          <Field
            label="Core value proposition"
            htmlFor="valueProp"
            required
            error={showError("valueProp")}
          >
            <Textarea
              {...text("valueProp")}
              placeholder="The single idea the company owns."
            />
          </Field>
          <Field
            label="Primary customer promise"
            htmlFor="promise"
            required
            error={showError("promise")}
          >
            <Input
              {...text("promise")}
              placeholder="What every customer can count on."
            />
          </Field>
          <Field
            label="Key differentiators"
            htmlFor="differentiators"
            required
            error={showError("differentiators")}
          >
            <Textarea
              {...text("differentiators")}
              placeholder="Why customers choose you over the alternatives."
            />
          </Field>
          <Field
            label="Defensible claims"
            htmlFor="claims"
            hint="One per line: Claim — evidence backing it"
          >
            <Textarea
              {...text("claims")}
              placeholder={'"Costs $0.31 per clean" — internal pricing model'}
            />
          </Field>
          <Field
            label="Main competitors"
            htmlFor="competitors"
            hint="One per line: Name — how we differ"
          >
            <Textarea
              {...text("competitors")}
              placeholder="Blueland — owns tablets; we own liquid concentrate"
            />
          </Field>
          <Field label="Positioning to avoid" htmlFor="avoid">
            <Input
              {...text("avoid")}
              placeholder="Topics or comparisons never to lead with."
            />
          </Field>
        </>
      )}

      {step === 3 && (
        <>
          <Field
            label="Brand personality"
            htmlFor="personality"
            required
            error={showError("personality")}
          >
            <Input
              {...text("personality")}
              placeholder="Plainspoken, confident, warm."
            />
          </Field>
          <Field
            label="Tone of voice"
            htmlFor="tone"
            required
            error={showError("tone")}
          >
            <Textarea
              {...text("tone")}
              placeholder="Short sentences. Real numbers. Never preachy."
            />
          </Field>
          <Field label="Writing style" htmlFor="writingStyle">
            <Input
              {...text("writingStyle")}
              placeholder="Specific over superlative."
            />
          </Field>
          <Field
            label="Prohibited terminology"
            htmlFor="prohibitedTerms"
            hint="One per line: Term — why it's off-limits"
          >
            <Textarea
              {...text("prohibitedTerms")}
              placeholder={'"eco-warrior" — alienates the practical buyer'}
            />
          </Field>
        </>
      )}

      {step === 4 && (
        <>
          <Field
            label="Restricted claims & terminology"
            htmlFor="restricted"
            required
            error={showError("restricted")}
            hint="One per line: Term — why it must never appear"
          >
            <Textarea
              {...text("restricted")}
              placeholder={'"non-toxic" — regulatory risk'}
            />
          </Field>
          <Field label="Required disclaimers" htmlFor="disclaimers">
            <Textarea
              {...text("disclaimers")}
              placeholder="Anything legal requires on published assets."
            />
          </Field>
        </>
      )}
    </WizardShell>
  );
}

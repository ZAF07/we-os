import {
  Container,
  Eyebrow,
  SectionHeading,
} from "@/components/public/section";

const STEPS = [
  {
    title: "Answer what only you know",
    text: "A curated questionnaire about the business: what it sells, who buys, what it costs, where it can reach. The answers become the Brand DNA every later decision is grounded in.",
  },
  {
    title: "Research, positioning and planning run in order",
    text: "Each stage reads the one before it. Research informs strategy, strategy informs the channel plan, the plan briefs the creative. Nothing is skipped and nothing is guessed.",
  },
  {
    title: "Approve each decision as it lands",
    text: "Each decision stops at a gate. Read the recommendation and the reason behind it, then approve it or send it back. Re-open something upstream and everything after it waits.",
  },
];

/**
 * Renders the three steps, and the anchor "See how it works" scrolls to.
 */
export function HowItWorks() {
  return (
    <section
      id="how"
      aria-labelledby="how-heading"
      className="mt-24 scroll-mt-(--top-bar-height) border-y bg-background"
    >
      <Container className="py-24">
        <div className="max-w-[640px]">
          <Eyebrow>How it works</Eyebrow>
          <SectionHeading id="how-heading">
            Three steps. Your judgement at each one.
          </SectionHeading>
        </div>
        <ol className="mt-14 grid gap-5 md:grid-cols-3">
          {STEPS.map((step, index) => (
            <li
              key={step.title}
              className="lift rounded-2xl border bg-card px-7 pt-7 pb-8"
            >
              <span
                aria-hidden="true"
                className="flex size-9 items-center justify-center rounded-[10px] bg-accent text-sm font-bold text-accent-foreground"
              >
                {index + 1}
              </span>
              <h3 className="mt-[18px] mb-2.5 text-xl font-semibold tracking-[-0.02em]">
                {step.title}
              </h3>
              <p className="text-[15px] leading-relaxed text-slate-600">
                {step.text}
              </p>
            </li>
          ))}
        </ol>
      </Container>
    </section>
  );
}

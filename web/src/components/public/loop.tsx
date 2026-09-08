import {
  Container,
  Eyebrow,
  SectionHeading,
} from "@/components/public/section";

/**
 * Renders the augmented loop: you answer, the specialists run, you approve.
 *
 * The one picture of what "augmented, not automated" means in practice, before
 * the steps are spelled out.
 */
export function Loop() {
  return (
    <section aria-labelledby="loop-heading" className="border-t">
      <Container className="pt-20">
        <div className="mb-10 grid items-end gap-6 md:grid-cols-2 md:gap-x-16">
          <div>
            <Eyebrow>Augmented, not automated</Eyebrow>
            <SectionHeading id="loop-heading">
              The work runs. You decide.
            </SectionHeading>
          </div>
          <p className="text-[16.5px] leading-relaxed text-slate-600">
            Every recommendation passes through your hands before it becomes a
            decision. The specialists prepare; you approve, send back, or
            re-open.
          </p>
        </div>
        <div className="grid items-center gap-3 rounded-[20px] border bg-background p-5 md:grid-cols-[1fr_auto_1fr_auto_1fr] md:gap-x-3 md:gap-y-0 md:p-9">
          <LoopCard
            badge="You"
            title="Answer"
            text="Business facts only you hold. They become the Brand DNA."
          />
          <Arrow />
          <LoopCard
            badge="×5"
            title="Specialists run"
            text="Research, strategy, plan, creative, prompts. Each shows its reasoning."
            dark
          />
          <Arrow />
          <LoopCard
            badge="✓"
            title="You approve"
            text="Approve, send back, or re-open upstream. Nothing runs otherwise."
            highlighted
          />
        </div>
      </Container>
    </section>
  );
}

/**
 * Renders one step of the loop.
 *
 * Args:
 *   badge: The short mark in the corner: who, or how many.
 *   title: The step.
 *   text: What happens in it.
 *   dark: Draw it on the dark card, for the part the specialists do.
 *   highlighted: Draw it with the primary border, for the decision.
 */
function LoopCard({
  badge,
  title,
  text,
  dark = false,
  highlighted = false,
}: {
  badge: string;
  title: string;
  text: string;
  dark?: boolean;
  highlighted?: boolean;
}) {
  const surface = dark
    ? "bg-slate-900 text-white"
    : highlighted
      ? "border-[1.5px] border-primary bg-card shadow-[0_10px_30px_-14px_rgba(79,70,229,0.5)]"
      : "border bg-card";
  const badgeSurface = dark
    ? "bg-white/10 text-indigo-300"
    : highlighted
      ? "bg-primary text-white"
      : "bg-accent text-accent-foreground";
  return (
    <div className={`flex flex-col gap-2.5 rounded-[14px] p-[22px] ${surface}`}>
      <span
        aria-hidden="true"
        className={`flex size-9 items-center justify-center rounded-[10px] text-[13px] font-bold ${badgeSurface}`}
      >
        {badge}
      </span>
      <span className="text-base font-semibold tracking-[-0.01em]">
        {title}
      </span>
      <span
        className={`text-[13.5px] leading-normal ${dark ? "text-slate-300" : "text-slate-600"}`}
      >
        {text}
      </span>
    </div>
  );
}

/** Renders the arrow between two steps; it points down when the steps stack. */
function Arrow() {
  return (
    <svg
      aria-hidden="true"
      width="56"
      height="24"
      viewBox="0 0 56 24"
      className="justify-self-center max-md:rotate-90"
    >
      <path
        d="M2 12h44"
        className="stroke-primary"
        strokeWidth="2"
        strokeDasharray="6 6"
      />
      <path
        d="M42 5l8 7-8 7"
        fill="none"
        className="stroke-primary"
        strokeWidth="2"
      />
    </svg>
  );
}

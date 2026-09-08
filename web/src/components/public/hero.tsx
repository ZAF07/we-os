import Link from "next/link";

import { Container } from "@/components/public/section";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * Renders the hero: the one-line promise, the two ways forward, and a picture
 * of the workflow paused at an approval gate.
 */
export function Hero() {
  return (
    <section className="relative overflow-hidden bg-[radial-gradient(1200px_600px_at_70%_-10%,var(--color-indigo-50),transparent_60%)]">
      <Container className="grid items-center gap-14 py-20 md:grid-cols-2 md:py-28">
        <div>
          <p className="mb-7 inline-flex items-center gap-2 rounded-full bg-accent py-1.5 pr-3 pl-2 text-[13px] font-semibold text-accent-foreground">
            <span
              aria-hidden="true"
              className="size-2 rounded-full bg-primary"
            />
            Augmented workflow for digital marketing
          </p>
          <h1 className="text-[clamp(42px,5.4vw,68px)] leading-[1.04] font-bold tracking-[-0.035em]">
            Strategy before content.{" "}
            <span className="text-primary sm:block">Always.</span>
          </h1>
          <p className="mt-6 max-w-[54ch] text-lg leading-relaxed text-slate-600">
            Expert practice built in, your judgement kept in. Answer the
            questions only you can answer, review each decision as it lands, and
            approve what runs.
          </p>
          <div className="mt-9 flex flex-wrap gap-3">
            <Button asChild size="xl">
              <Link href="/sign-up">Get started</Link>
            </Button>
            <Button asChild size="xl" variant="outline">
              <Link href="#how">See how it works</Link>
            </Button>
          </div>
        </div>
        <HeroPipeline />
      </Container>
    </section>
  );
}

type StageState = "complete" | "approved" | "gate" | "waiting";

const STAGES: Array<{ name: string; state: StageState }> = [
  { name: "Brand DNA, answered by you", state: "complete" },
  { name: "Research", state: "complete" },
  { name: "Brand strategy", state: "approved" },
  { name: "Campaign strategy", state: "approved" },
  { name: "Performance plan", state: "gate" },
  { name: "Creative brief", state: "waiting" },
  { name: "Asset prompts", state: "waiting" },
];

/**
 * Renders the workflow as a campaign card paused at an approval gate.
 *
 * Drawn from the theme tokens, no image. It is an illustration, so the whole
 * card is one labelled picture to assistive technology rather than a list of
 * chips that mean nothing out of context. The stages are the real ones, in
 * the real order, so what a visitor sees here is what they get.
 */
function HeroPipeline() {
  return (
    <div
      role="img"
      aria-label="A campaign paused at the performance plan approval gate: the Brand DNA, research and both strategy stages done, the creative brief and asset prompts waiting on the decision."
      className="relative"
    >
      <div
        aria-hidden="true"
        className="absolute -inset-10 rounded-full bg-[radial-gradient(closest-side,rgba(79,70,229,0.14),transparent_70%)] blur-3xl"
      />
      <div className="relative overflow-hidden rounded-[20px] border bg-card shadow-[0_30px_80px_-30px_rgba(15,23,42,0.25),0_2px_6px_rgba(15,23,42,0.04)]">
        <div className="flex items-center justify-between gap-3 border-b px-5 py-4">
          <div className="flex items-center gap-2.5">
            <span className="text-[15px] font-semibold">
              First product launch
            </span>
            <span className="rounded-full bg-slate-100 px-2 py-[3px] text-xs text-slate-500">
              3/6 stages
            </span>
          </div>
          <span className="rounded-full bg-accent px-2.5 py-1 text-xs font-semibold text-accent-foreground">
            Needs you
          </span>
        </div>
        <div className="px-3 pt-2 pb-3">
          {STAGES.map((stage) =>
            stage.state === "gate" ? (
              <GateRow key={stage.name} name={stage.name} />
            ) : (
              <StageRow
                key={stage.name}
                name={stage.name}
                state={stage.state}
              />
            ),
          )}
        </div>
      </div>
    </div>
  );
}

const STAGE_PRESENTATION: Record<
  Exclude<StageState, "gate">,
  { label: string; done: boolean }
> = {
  complete: { label: "Complete", done: true },
  approved: { label: "Approved", done: true },
  waiting: { label: "Waiting", done: false },
};

/**
 * Renders one stage that is not the one waiting on a decision.
 *
 * Args:
 *   name: The stage name.
 *   state: Whether it is done or still to come.
 */
function StageRow({
  name,
  state,
}: {
  name: string;
  state: Exclude<StageState, "gate">;
}) {
  const { label, done } = STAGE_PRESENTATION[state];
  return (
    <div
      className={cn(
        "grid grid-cols-[24px_1fr_auto] items-center gap-3 px-2.5 py-3",
        !done && "text-slate-400",
      )}
    >
      {done ? (
        <span className="flex size-[22px] items-center justify-center rounded-full bg-emerald-100 text-xs font-bold text-emerald-600">
          ✓
        </span>
      ) : (
        <span className="size-[22px] rounded-full border-[1.5px] border-dashed border-slate-300" />
      )}
      <span className={cn("text-[14.5px]", done && "text-slate-700")}>
        {name}
      </span>
      {done ? (
        <span className="rounded-full bg-emerald-100 px-2 py-[3px] text-xs font-semibold text-emerald-600">
          {label}
        </span>
      ) : (
        <span className="text-xs">{label}</span>
      )}
    </div>
  );
}

/**
 * Renders the stage holding at its approval gate, with the recommendation and
 * the reason behind it.
 *
 * Args:
 *   name: The stage name.
 */
function GateRow({ name }: { name: string }) {
  return (
    <div className="my-1 rounded-xl border-[1.5px] border-primary bg-indigo-50/60 p-3.5">
      <div className="grid grid-cols-[24px_1fr] items-start gap-3">
        <span className="mt-px flex size-[22px] items-center justify-center rounded-full bg-primary">
          <span className="size-2 rounded-full bg-white" />
        </span>
        <div>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-[14.5px] font-semibold">{name}</span>
            <span className="text-[11.5px] font-semibold tracking-[0.02em] text-accent-foreground uppercase">
              Approval gate
            </span>
          </div>
          <p className="mt-1.5 text-[13.5px] leading-normal text-slate-600">
            Concentrate the budget on two channels rather than five. Why: the
            segment&apos;s reach and cost per acquisition, from the research.
          </p>
          <div className="mt-3 flex gap-2">
            <span className="rounded-[9px] bg-primary px-3.5 py-2 text-[13px] font-semibold text-white">
              Approve
            </span>
            <span className="rounded-[9px] border bg-card px-3.5 py-2 text-[13px] font-semibold">
              Send back
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

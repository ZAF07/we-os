import Link from "next/link";

import { Button } from "@/components/ui/button";

/**
 * Renders the Landing: what We-OS is, for a visitor deciding whether it is for
 * them.
 *
 * A static server component with no engine call and no session, so it is fast
 * and can never show an engine error. The copy lives here rather than in a
 * content system, and it is the product's public voice: an augmented workflow
 * with the owner's judgement kept in.
 */
export default function LandingPage() {
  return (
    <main>
      <Hero />
    </main>
  );
}

/** Renders the hero: the one-line promise and the two ways forward. */
function Hero() {
  return (
    <section className="relative overflow-hidden bg-[radial-gradient(1200px_600px_at_70%_-10%,var(--color-indigo-50),transparent_60%)]">
      <div className="mx-auto grid max-w-[1180px] items-center gap-14 px-5 py-20 md:grid-cols-2 md:px-10 md:py-28">
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
      </div>
    </section>
  );
}

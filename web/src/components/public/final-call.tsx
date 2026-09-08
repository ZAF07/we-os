import Link from "next/link";

import { Container } from "@/components/public/section";
import { Button } from "@/components/ui/button";

/** Renders the final call: one line, and the way in. */
export function FinalCall() {
  return (
    <section
      id="start"
      aria-labelledby="start-heading"
      className="scroll-mt-(--top-bar-height)"
    >
      <Container className="pb-24">
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-indigo-600 to-indigo-700 p-12 text-white md:p-20">
          <div
            aria-hidden="true"
            className="absolute -top-[120px] -right-[120px] size-[420px] rounded-full bg-white/[0.08]"
          />
          <div
            aria-hidden="true"
            className="absolute right-20 -bottom-[200px] size-[360px] rounded-full bg-white/[0.06]"
          />
          <h2
            id="start-heading"
            className="relative max-w-[18ch] text-[clamp(32px,4.2vw,54px)] leading-[1.06] font-bold tracking-[-0.035em]"
          >
            Answer the questions. Approve what runs.
          </h2>
          <p className="relative mt-5 max-w-[50ch] text-[17px] leading-relaxed text-indigo-100">
            Start with the Brand DNA. The first campaign is a few approvals
            away.
          </p>
          <div className="relative mt-9 flex flex-wrap gap-3">
            <Button
              asChild
              size="xl"
              className="bg-white text-indigo-700 hover:bg-indigo-50"
            >
              <Link href="/sign-up">Get started</Link>
            </Button>
            <Button
              asChild
              size="xl"
              variant="outline"
              className="border-white/40 bg-transparent text-white hover:bg-white/10 hover:text-white"
            >
              <Link href="/sign-in">Sign in</Link>
            </Button>
          </div>
        </div>
      </Container>
    </section>
  );
}

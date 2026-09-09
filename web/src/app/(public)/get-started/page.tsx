import type { Metadata } from "next";
import { auth } from "@clerk/nextjs/server";

import { Faq } from "@/components/public/faq";
import {
  Container,
  Eyebrow,
  SectionHeading,
} from "@/components/public/section";
import { TierCards } from "@/components/public/tier-card";
import { launchHref } from "@/lib/tiers";

export const metadata: Metadata = {
  title: "Get started",
  description:
    "Choose a tier to start with. Every tier includes the whole of We-OS and differs only in monthly credits.",
};

/**
 * Renders Get Started: the funnel step where a visitor chooses a tier before
 * an account exists.
 *
 * The same tier cards and the same questions as Pricing, rendered by the same
 * components so the two pages cannot show two sets of numbers. What differs is
 * the job: Pricing explains what it costs, this page asks for the decision,
 * and its heading says so. There is no final-call section because the page is
 * the call.
 *
 * It reads the Clerk session — and makes no engine call, so the public half's
 * no-engine property holds — because where Launch leads depends on it: a
 * visitor goes to sign-up, a signed-in person to Welcome, with the tier either
 * way.
 */
export default async function GetStartedPage() {
  const { userId } = await auth();
  const session = { signedIn: userId !== null };

  return (
    <main>
      <section aria-labelledby="get-started-heading">
        <Container className="pt-20 pb-24 md:pt-24">
          <div className="max-w-[640px]">
            <Eyebrow>Get started</Eyebrow>
            <SectionHeading id="get-started-heading" as="h1">
              Choose your tier.
            </SectionHeading>
            <p className="mt-4 text-[16.5px] leading-relaxed text-slate-600">
              Every tier includes the whole product. Pick the credits your
              business will use each month, then create your login.
            </p>
          </div>
          <TierCards destination={(tier) => launchHref(tier, session)} />
        </Container>
      </section>
      <Faq />
    </main>
  );
}

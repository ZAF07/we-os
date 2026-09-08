import type { Metadata } from "next";

import { Faq } from "@/components/public/faq";
import { FinalCall } from "@/components/public/final-call";
import { PricingIntro } from "@/components/public/pricing-section";
import { Container } from "@/components/public/section";
import { TierCards } from "@/components/public/tier-card";

export const metadata: Metadata = {
  title: "Pricing",
  description:
    "Three tiers, one product. Every tier includes the whole of We-OS and differs only in monthly credits.",
};

/**
 * Renders Pricing: the three tiers, the questions people ask before paying,
 * and the way in, on a page a visitor can send to a colleague.
 *
 * A static server component with no engine call and no session. The tiers
 * and the FAQ come from the same components the Landing uses, so the two
 * pages never disagree.
 */
export default function PricingPage() {
  return (
    <main>
      <section aria-labelledby="pricing-heading">
        <Container className="pt-20 pb-24 md:pt-24">
          <PricingIntro as="h1" />
          <TierCards />
        </Container>
      </section>
      <Faq />
      <FinalCall />
    </main>
  );
}

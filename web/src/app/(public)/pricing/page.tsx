import type { Metadata } from "next";

import { Faq } from "@/components/public/faq";
import { FinalCall } from "@/components/public/final-call";
import {
  Container,
  Eyebrow,
  SectionHeading,
} from "@/components/public/section";
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
 * A static server component with no engine call and no session. It is the
 * only place the tiers appear, so a visitor never sees two prices; the FAQ is
 * the same component the Landing shows.
 */
export default function PricingPage() {
  return (
    <main>
      <section aria-labelledby="pricing-heading">
        <Container className="pt-20 pb-24 md:pt-24">
          <div className="max-w-[640px]">
            <Eyebrow>Pricing</Eyebrow>
            <SectionHeading id="pricing-heading" as="h1">
              The whole product, on every tier.
            </SectionHeading>
            <p className="mt-4 text-[16.5px] leading-relaxed text-slate-600">
              Tiers differ only in monthly credits. A credit is what your
              business spends on generation, and every tier grants a fresh set
              each month.
            </p>
          </div>
          <TierCards />
        </Container>
      </section>
      <Faq />
      <FinalCall />
    </main>
  );
}

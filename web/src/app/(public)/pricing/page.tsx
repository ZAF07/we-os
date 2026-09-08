import type { Metadata } from "next";

import { Eyebrow } from "@/components/public/section";
import { TierCards } from "@/components/public/tier-card";

export const metadata: Metadata = {
  title: "Pricing",
  description:
    "Three tiers, one product. Every tier includes the whole of We-OS and differs only in monthly credits.",
};

/**
 * Renders Pricing: the three tiers, on a page a visitor can send to a
 * colleague.
 *
 * A static server component with no engine call and no session. The tiers
 * come from the same module and the same card as the Landing's pricing
 * section, so the two never disagree.
 */
export default function PricingPage() {
  return (
    <main>
      <section
        aria-labelledby="pricing-heading"
        className="mx-auto max-w-[1180px] px-5 py-20 md:px-10 md:py-24"
      >
        <div className="max-w-[640px]">
          <Eyebrow>Pricing</Eyebrow>
          <h1
            id="pricing-heading"
            className="text-[clamp(30px,3.6vw,44px)] leading-[1.1] font-bold tracking-[-0.03em]"
          >
            The whole product, on every tier.
          </h1>
          <p className="mt-4 text-[16.5px] leading-relaxed text-slate-600">
            Tiers differ only in monthly credits. A credit is what your business
            spends on generation, and every tier grants a fresh set each month.
          </p>
        </div>
        <TierCards />
      </section>
    </main>
  );
}

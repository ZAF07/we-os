import {
  Container,
  Eyebrow,
  SectionHeading,
} from "@/components/public/section";
import { TierCards } from "@/components/public/tier-card";

/**
 * Renders the words above the tier cards: the promise that every tier gets
 * the whole product, and what a credit is.
 *
 * Shared by the Landing's pricing section and the Pricing page, so the
 * explanation of a credit is the same wherever the tiers are read.
 *
 * Args:
 *   as: The heading level: `h2` on the Landing, `h1` on the Pricing page.
 */
export function PricingIntro({ as = "h2" }: { as?: "h1" | "h2" }) {
  return (
    <div className="max-w-[640px]">
      <Eyebrow>Pricing</Eyebrow>
      <SectionHeading id="pricing-heading" as={as}>
        The whole product, on every tier.
      </SectionHeading>
      <p className="mt-4 text-[16.5px] leading-relaxed text-slate-600">
        Tiers differ only in monthly credits. A credit is what your business
        spends on generation, and every tier grants a fresh set each month.
      </p>
    </div>
  );
}

/**
 * Renders the Landing's pricing section, from the same cards the Pricing page
 * shows.
 */
export function PricingSection() {
  return (
    <section
      id="pricing"
      aria-labelledby="pricing-heading"
      className="scroll-mt-(--top-bar-height) border-b bg-background"
    >
      <Container className="py-24">
        <PricingIntro />
        <TierCards />
      </Container>
    </section>
  );
}

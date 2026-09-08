import {
  Container,
  Eyebrow,
  SectionHeading,
} from "@/components/public/section";
import { TierCards } from "@/components/public/tier-card";

/**
 * Renders the Landing's pricing section, from the same cards the Pricing page
 * shows.
 */
export function PricingSection() {
  return (
    <section
      id="pricing"
      aria-labelledby="pricing-heading"
      className="scroll-mt-[68px] border-b bg-background"
    >
      <Container className="py-24">
        <div className="max-w-[640px]">
          <Eyebrow>Pricing</Eyebrow>
          <SectionHeading id="pricing-heading">
            The whole product, on every tier.
          </SectionHeading>
          <p className="mt-4 text-[16.5px] leading-relaxed text-slate-600">
            Tiers differ only in monthly credits. A credit is what your business
            spends on generation, and every tier grants a fresh set each month.
          </p>
        </div>
        <TierCards />
      </Container>
    </section>
  );
}

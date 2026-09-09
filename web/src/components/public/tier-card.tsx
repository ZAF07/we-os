import Link from "next/link";

import { Button } from "@/components/ui/button";
import { signUpHref, TIERS, type Tier } from "@/lib/tiers";
import { cn } from "@/lib/utils";

/**
 * Renders one tier: name, price, credits, who it suits, and the way in.
 *
 * The highlighted tier is labelled "Recommended" rather than "Most chosen":
 * a recommendation is the product's to make, while popularity would be a
 * claim about other businesses that nothing backs yet.
 *
 * The one component that renders a tier, so every place that shows one
 * agrees: Pricing and Get Started. Its button says "Launch" — the action that
 * will one day open checkout, and today opens sign-up carrying the tier — so
 * the two pages cannot disagree on what pressing it means.
 *
 * Args:
 *   tier: The tier to show.
 *   destination: Where Launch leads for this tier.
 */
export function TierCard({
  tier,
  destination,
}: {
  tier: Tier;
  destination: (tier: Tier) => string;
}) {
  const headingId = `tier-${tier.name.toLowerCase()}`;
  const credits = new Intl.NumberFormat("en-US").format(tier.monthlyCredits);

  return (
    <article
      aria-labelledby={headingId}
      className={cn(
        "lift flex flex-col gap-[18px] rounded-[20px] border bg-card p-8",
        tier.highlighted &&
          "border-2 border-primary shadow-[0_20px_50px_-24px_rgba(79,70,229,0.45)]",
      )}
    >
      <div className="flex min-h-6 items-center justify-between gap-3">
        <h3 id={headingId} className="text-lg font-semibold tracking-[-0.01em]">
          {tier.name}
        </h3>
        {tier.highlighted && (
          <span className="rounded-full bg-accent px-2.5 py-1 text-xs font-semibold text-accent-foreground">
            Recommended
          </span>
        )}
      </div>
      <p className="text-[44px] leading-none font-bold tracking-[-0.035em]">
        ${tier.monthlyPriceUsd}
        <span className="text-[15px] font-medium tracking-normal text-slate-500">
          {" "}
          / month
        </span>
      </p>
      <p className="text-[15px]">
        <strong>{credits}</strong> credits a month
      </p>
      <p className="flex-1 text-[15px] leading-relaxed text-slate-600">
        {tier.suits}
      </p>
      <p className="text-[13.5px] leading-relaxed text-slate-500">
        Everything included: every stage, every specialist, your full Brand DNA.
      </p>
      <Button
        asChild
        size="xl"
        variant={tier.highlighted ? "default" : "outline"}
        className="w-full"
      >
        <Link href={destination(tier)}>Launch</Link>
      </Button>
    </article>
  );
}

/**
 * Renders the three tiers side by side, with the one line that is true of all
 * of them.
 *
 * No trial, refund or cancellation term is promised here, because the product
 * cannot honour one yet.
 *
 * Args:
 *   destination: Where each tier's Launch leads. Pricing keeps the default,
 *     sign-up carrying the tier; Get Started resolves it from the session.
 */
export function TierCards({
  destination = signUpHref,
}: {
  destination?: (tier: Tier) => string;
}) {
  return (
    <>
      <div className="mt-14 grid items-stretch gap-5 md:grid-cols-3">
        {TIERS.map((tier) => (
          <TierCard key={tier.name} tier={tier} destination={destination} />
        ))}
      </div>
      <p className="mt-6 text-[13.5px] text-slate-500">
        Prices in USD. Every tier includes the whole product and differs only in
        credits.
      </p>
    </>
  );
}

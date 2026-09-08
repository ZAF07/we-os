import Link from "next/link";

import { Button } from "@/components/ui/button";
import { signUpHref, TIERS, type Tier } from "@/lib/tiers";
import { cn } from "@/lib/utils";

/**
 * Renders one tier: name, price, credits, who it suits, and the way in.
 *
 * The one component both the Landing's pricing section and the Pricing page
 * use, so the two can never show different tiers.
 *
 * Args:
 *   tier: The tier to show.
 */
export function TierCard({ tier }: { tier: Tier }) {
  const headingId = `tier-${tier.name.toLowerCase()}`;
  const credits = new Intl.NumberFormat("en-US").format(tier.monthlyCredits);

  return (
    <article
      aria-labelledby={headingId}
      className={cn(
        "flex flex-col gap-[18px] rounded-[20px] border bg-card p-8 transition-[transform,box-shadow] duration-200 hover:-translate-y-0.5 hover:shadow-[0_16px_40px_-16px_rgba(15,23,42,0.2)]",
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
            Most chosen
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
        {tier.audience}
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
        <Link href={signUpHref(tier)}>Get started</Link>
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
 */
export function TierCards() {
  return (
    <>
      <div className="mt-14 grid items-stretch gap-5 md:grid-cols-3">
        {TIERS.map((tier) => (
          <TierCard key={tier.name} tier={tier} />
        ))}
      </div>
      <p className="mt-6 text-[13.5px] text-slate-500">
        Prices in USD. Every tier includes the whole product and differs only in
        credits.
      </p>
    </>
  );
}

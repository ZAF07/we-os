/**
 * The three tiers a business picks from at sign-up, defined once.
 *
 * Tiers differ only in the credits they grant each month; every tier gets the
 * whole product. Prices and credit amounts are placeholders until pricing is
 * decided, so they live here and nowhere else: when the real numbers arrive,
 * this module is the only place that changes, and every page that shows a tier
 * follows.
 */

export type TierName = "Operator" | "Strategist" | "Command";

export interface Tier {
  name: TierName;
  monthlyPriceUsd: number;
  monthlyCredits: number;
  suits: string;
  highlighted: boolean;
}

export const TIERS: readonly Tier[] = [
  {
    name: "Operator",
    monthlyPriceUsd: 59,
    monthlyCredits: 6_000,
    suits: "For one business finding its footing.",
    highlighted: false,
  },
  {
    name: "Strategist",
    monthlyPriceUsd: 89,
    monthlyCredits: 10_000,
    suits: "For a business running campaigns every month.",
    highlighted: true,
  },
  {
    name: "Command",
    monthlyPriceUsd: 115,
    monthlyCredits: 20_000,
    suits: "For a business that never stops marketing.",
    highlighted: false,
  },
];

/**
 * Builds the sign-up address for a tier.
 *
 * The tier travels as a query parameter holding the lowercase tier name, so a
 * visitor's choice is not lost between the page and the sign-up form.
 *
 * Args:
 *   tier: The tier the visitor chose.
 *
 * Returns:
 *   The sign-up path with the tier parameter.
 */
export function signUpHref(tier: Tier): string {
  return `/sign-up?tier=${tier.name.toLowerCase()}`;
}

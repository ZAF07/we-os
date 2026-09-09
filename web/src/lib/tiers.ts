/**
 * The three tiers a business picks from at sign-up, defined once.
 *
 * Tiers differ only in the credits they grant each month; every tier gets the
 * whole product. Prices and credit amounts are placeholders until pricing is
 * decided, so they live here and nowhere else: when the real numbers arrive,
 * this module is the only place that changes, and every page that shows a tier
 * follows.
 *
 * The engine knows the same three names, and nothing else about a tier, as the
 * `TierName` literal in `agent-harness/src/marketing_os/schemas.py`. The two
 * lists point at each other: rename a tier here and the engine must follow, or
 * recording it at Welcome is refused.
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
 * Returns the name a tier travels under: in a query parameter, and to the
 * engine, which spells its tiers this way.
 *
 * Args:
 *   tier: The tier.
 *
 * Returns:
 *   The lowercase tier name.
 */
export function tierParam(tier: Tier): string {
  return tier.name.toLowerCase();
}

/**
 * Builds the sign-up address for a tier.
 *
 * The tier travels as a query parameter holding the lowercase tier name, so a
 * visitor's choice is not lost between the page and the sign-up form. The
 * sign-up page reads it back and sends the new person on to Welcome with it.
 *
 * Args:
 *   tier: The tier the visitor chose.
 *
 * Returns:
 *   The sign-up path with the tier parameter.
 */
export function signUpHref(tier: Tier): string {
  return `/sign-up?tier=${tierParam(tier)}`;
}

/**
 * Reads the tier a query parameter names.
 *
 * The one place the parameter is decoded, mirroring `tierParam`, which is the
 * one place it is encoded. Forgiving about case, since a person may type the
 * address; strict about the name, since an unknown one is not a tier.
 *
 * Args:
 *   value: The parameter as Next.js hands it over: a string, a list when it
 *     was repeated, or nothing.
 *
 * Returns:
 *   The tier, or null when the parameter names none.
 */
export function tierFromParam(
  value: string | string[] | undefined,
): Tier | null {
  const name = (Array.isArray(value) ? value[0] : value)?.toLowerCase();
  if (!name) return null;
  return TIERS.find((tier) => tierParam(tier) === name) ?? null;
}

/** The query string as Next.js hands it to a page, read for the tier it carries. */
export type TierSearchParams = Promise<{ tier?: string | string[] }>;

/**
 * Reads the tier a page's query string names.
 *
 * Args:
 *   searchParams: The page's search params, as Next.js provides them.
 *
 * Returns:
 *   The tier, or null when the query string names none.
 */
export async function tierFromSearchParams(
  searchParams: TierSearchParams,
): Promise<Tier | null> {
  return tierFromParam((await searchParams).tier);
}

/**
 * Builds the Welcome address, carrying the tier when there is one.
 *
 * Bare Welcome is where a person with no tier lands, and Welcome sends them to
 * Get Started to choose one — so a business is never created with a tier
 * nobody picked.
 *
 * Args:
 *   tier: The tier chosen, or null when none was.
 *
 * Returns:
 *   The Welcome path, with the tier parameter when a tier was chosen.
 */
export function welcomeHref(tier: Tier | null): string {
  return tier ? `/welcome?tier=${tierParam(tier)}` : "/welcome";
}

/** What Get Started knows about the person pressing Launch. */
export interface LaunchSession {
  signedIn: boolean;
}

/**
 * Resolves where a tier's Launch button on Get Started leads.
 *
 * A visitor goes to sign-up with the tier. A signed-in person already has an
 * account, so they go to Welcome with the tier instead: a new person to name
 * their business, a business owner to have the tier recorded — which Welcome
 * refuses if the business already has a different one. Pricing does not use
 * this: its Launch keeps the sign-up address, because someone deciding there
 * has already made the choice Get Started exists to extract.
 *
 * Args:
 *   tier: The tier the person chose.
 *   session: Whether they are signed in.
 *
 * Returns:
 *   The path Launch opens.
 */
export function launchHref(tier: Tier, session: LaunchSession): string {
  return session.signedIn ? welcomeHref(tier) : signUpHref(tier);
}

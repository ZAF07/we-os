import type { Metadata } from "next";
import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";

import { WelcomeForm } from "@/components/welcome/welcome-form";
import { tierFromParam, tierParam } from "@/lib/tiers";

export const metadata: Metadata = { title: "Welcome" };

export const dynamic = "force-dynamic";

/**
 * Renders Welcome: where a person who has authenticated but has no business
 * yet names it.
 *
 * Two redirects and no engine call. With no tier there is nothing to record,
 * so a person without a business is sent to Get Started to choose one — a
 * business is never created with a tier nobody picked — and a person with a
 * business is sent to Home, since there is nothing here for them. With a tier,
 * the form takes over: it names the business when there is none, and when the
 * session already carries one it records the tier and continues. That second
 * path is how a business whose tier was never recorded finishes: Home sends it
 * to choose, and Launch brings it back here with the choice.
 *
 * No session never reaches this far; the proxy sends it to sign-in.
 *
 * Args:
 *   searchParams: The query string, read for the tier Launch carried.
 */
export default async function WelcomePage({
  searchParams,
}: {
  searchParams: Promise<{ tier?: string | string[] }>;
}) {
  const tier = tierFromParam((await searchParams).tier);
  const { orgId } = await auth();
  const businessExists = Boolean(orgId);

  if (tier === null) redirect(businessExists ? "/home" : "/get-started");

  return (
    <WelcomeForm
      tier={tierParam(tier)}
      tierName={tier.name}
      businessExists={businessExists}
    />
  );
}

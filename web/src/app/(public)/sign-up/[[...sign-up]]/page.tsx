import { SignUp } from "@clerk/nextjs";

import { tierFromParam, welcomeHref } from "@/lib/tiers";

/**
 * Clerk's hosted sign-up flow, under the public layout.
 *
 * Clerk creates the person and nothing else: the business is created by We-OS
 * on Welcome, after a tier has been chosen (ADR-0027). So once authentication
 * completes the new person is sent to Welcome carrying the tier this page was
 * opened with — or to bare Welcome when it was opened with none, which sends
 * them to Get Started to choose one. The destination is forced rather than a
 * fallback: a new person never has a business to return to.
 *
 * An existing person who signs in from this form has a business and needs no
 * welcome, so the sign-in fallback stays Home.
 *
 * Args:
 *   searchParams: The query string, read for the tier a tier card carried.
 */
export default async function SignUpPage({
  searchParams,
}: {
  searchParams: Promise<{ tier?: string | string[] }>;
}) {
  const tier = tierFromParam((await searchParams).tier);

  return (
    <main className="flex flex-1 items-center justify-center px-6 py-16">
      <div className="flex w-full max-w-md flex-col items-center gap-8">
        <div className="text-center">
          <h1 className="text-2xl font-semibold tracking-tight">We-OS</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Create your login. You name your business next.
          </p>
        </div>
        <SignUp
          forceRedirectUrl={welcomeHref(tier)}
          signInFallbackRedirectUrl="/home"
        />
      </div>
    </main>
  );
}

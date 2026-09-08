import { SignUp } from "@clerk/nextjs";

/**
 * Clerk's hosted sign-up flow, under the public layout.
 *
 * Clerk is configured to create an Organization on sign-up: one Organization is
 * one business is one We-OS tenant, so a new account lands with a tenant that
 * the engine can derive from its token claim (ADR-0013). It falls back to Home
 * once done, so the next step — onboarding — is in front of the new owner.
 *
 * A `tier` query parameter may arrive from a tier card. It is carried, not
 * read: nothing consumes it until billing exists.
 */
export default function SignUpPage() {
  return (
    <main className="flex flex-1 items-center justify-center px-6 py-16">
      <div className="flex w-full max-w-md flex-col items-center gap-8">
        <div className="text-center">
          <h1 className="text-2xl font-semibold tracking-tight">We-OS</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Create the account your business&apos;s marketing lives in.
          </p>
        </div>
        <SignUp fallbackRedirectUrl="/home" signInFallbackRedirectUrl="/home" />
      </div>
    </main>
  );
}

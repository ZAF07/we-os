import { SignUp } from "@clerk/nextjs";

/**
 * Clerk's hosted sign-up flow.
 *
 * Clerk is configured to create an Organization on sign-up: one Organization is
 * one business is one we-OS tenant, so a new account lands with a tenant that
 * the engine can derive from its token claim (ADR-0013).
 */
export default function SignUpPage() {
  return (
    <main className="flex min-h-dvh items-center justify-center bg-background p-6">
      <div className="flex w-full max-w-md flex-col items-center gap-8">
        <div className="text-center">
          <h1 className="text-2xl font-semibold tracking-tight">we-OS</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Create the account your business&apos;s marketing lives in.
          </p>
        </div>
        <SignUp />
      </div>
    </main>
  );
}

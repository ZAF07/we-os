import { SignIn } from "@clerk/nextjs";

/**
 * Clerk's hosted sign-in flow, under the public layout.
 *
 * Falls back to Home once signed in, so a returning business owner lands on
 * what needs them rather than on the Landing. A return address set by the
 * proxy when it bounced a signed-out request still wins, so a stale session
 * costs one click, not a place.
 */
export default function SignInPage() {
  return (
    <main className="flex flex-1 items-center justify-center px-6 py-16">
      <div className="flex w-full max-w-md flex-col items-center gap-8">
        <div className="text-center">
          <h1 className="text-2xl font-semibold tracking-tight">We-OS</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Sign in to your marketing department.
          </p>
        </div>
        <SignIn fallbackRedirectUrl="/home" signUpFallbackRedirectUrl="/home" />
      </div>
    </main>
  );
}

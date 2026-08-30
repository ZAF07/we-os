import { SignIn } from "@clerk/nextjs";

/** Clerk's hosted sign-in flow, rendered on its own full-page route. */
export default function SignInPage() {
  return (
    <main className="flex min-h-dvh items-center justify-center bg-background p-6">
      <div className="flex w-full max-w-md flex-col items-center gap-8">
        <div className="text-center">
          <h1 className="text-2xl font-semibold tracking-tight">we-OS</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Sign in to your marketing department.
          </p>
        </div>
        <SignIn />
      </div>
    </main>
  );
}

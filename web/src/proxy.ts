import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

/**
 * Routes reachable without a session: the sign-in and sign-up flows themselves,
 * and Clerk's own callback handling. Everything else requires a signed-in user.
 */
const isPublicRoute = createRouteMatcher(["/sign-in(.*)", "/sign-up(.*)"]);

/**
 * Sends signed-out visitors to the sign-in page rather than refusing them.
 *
 * `auth.protect()` answers 404 for an unauthenticated page request, which is
 * right for an API but leaves a person with no way to reach the login screen.
 * Redirecting is the correct behaviour for a rendered route.
 *
 * This is a convenience, not the security boundary. Every route that reads
 * tenant data does so through the engine, which verifies the token itself and
 * refuses an unauthenticated call regardless of how the request got here
 * (ADR-0013).
 */
export default clerkMiddleware(async (auth, request) => {
  if (isPublicRoute(request)) return;

  const { userId, redirectToSignIn } = await auth();
  if (!userId) {
    return redirectToSignIn({ returnBackUrl: request.url });
  }
});

/**
 * Runs on everything except Next.js internals and static files, unless a search
 * param is present — so server actions on static-looking paths still pass
 * through auth.
 */
export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};

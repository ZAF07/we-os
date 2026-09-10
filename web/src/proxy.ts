import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

/**
 * The public half: the Landing, Pricing, Get Started, and the sign-in and
 * sign-up flows with Clerk's own callback handling. Everything else is the app
 * half and requires a signed-in user.
 */
const isPublicRoute = createRouteMatcher([
  "/",
  "/pricing",
  "/get-started",
  "/sign-in(.*)",
  "/sign-up(.*)",
]);

/** The Landing: a visitor's page, so a signed-in business gets Home instead. */
const isLanding = createRouteMatcher(["/"]);

/** Welcome: the one signed-in route a session with no business may reach. */
const isWelcome = createRouteMatcher(["/welcome"]);

/**
 * Sends each request to the half of the app that is for it.
 *
 * A signed-in session that opens the root is sent to Home: the Landing is for
 * a visitor deciding, and a business owner working should never see the sales
 * page. A signed-out request for an app route goes to the sign-in page rather
 * than being refused, with its address kept so the person returns to where
 * they were. `auth.protect()` would answer 404, which is right for an API but
 * leaves a person with no way to reach the login screen.
 *
 * The address is kept as a path, not as `request.url`: Next fills that in
 * with the address the server is bound to, which under `next dev --hostname
 * 0.0.0.0` (the e2e stack) is `0.0.0.0:3000` rather than the host the browser
 * used. Clerk resolves a relative return URL against the browser-facing URL,
 * but refuses an absolute one whose origin it does not know and sends the
 * person to Home instead — which is how a transient session miss turned into
 * a spec landing on the wrong screen.
 *
 * A signed-in session whose token carries no organization claim — a Tenantless
 * Session, a new person between authenticating and naming their business — may
 * reach only Welcome and the public routes. Anything else in the app half goes
 * to Welcome, so there is always a way forward and never a way around. The
 * claim is already in the token, so this costs no engine call on any request.
 *
 * This is a convenience, not the security boundary. Every route that reads
 * tenant data does so through the engine, which verifies the token itself and
 * refuses an unauthenticated call — or one with no organization claim —
 * regardless of how the request got here (ADR-0013).
 */
export default clerkMiddleware(async (auth, request) => {
  const { userId, orgId, redirectToSignIn } = await auth();

  if (isLanding(request) && userId) {
    return NextResponse.redirect(new URL("/home", request.url));
  }
  if (isPublicRoute(request)) return;
  if (!userId) {
    return redirectToSignIn({
      returnBackUrl: request.nextUrl.pathname + request.nextUrl.search,
    });
  }
  if (!orgId && !isWelcome(request)) {
    return NextResponse.redirect(new URL("/welcome", request.url));
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

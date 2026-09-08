import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

/**
 * The public half: the Landing, and the sign-in and sign-up flows with Clerk's
 * own callback handling. Everything else is the app half and requires a
 * signed-in user.
 */
const isPublicRoute = createRouteMatcher(["/", "/sign-in(.*)", "/sign-up(.*)"]);

/** The Landing — two pages for two audiences, and a tenant gets Home. */
const isLanding = createRouteMatcher(["/"]);

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
 * This is a convenience, not the security boundary. Every route that reads
 * tenant data does so through the engine, which verifies the token itself and
 * refuses an unauthenticated call regardless of how the request got here
 * (ADR-0013).
 */
export default clerkMiddleware(async (auth, request) => {
  const { userId, redirectToSignIn } = await auth();

  if (isLanding(request) && userId) {
    return NextResponse.redirect(new URL("/home", request.url));
  }
  if (isPublicRoute(request)) return;
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

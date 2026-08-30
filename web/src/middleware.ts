import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

/**
 * Routes reachable without a session: the sign-in and sign-up flows themselves,
 * and Clerk's own callback handling. Everything else requires a signed-in user.
 */
const isPublicRoute = createRouteMatcher([
  "/sign-in(.*)",
  "/sign-up(.*)",
]);

export default clerkMiddleware(async (auth, request) => {
  if (!isPublicRoute(request)) {
    await auth.protect();
  }
});

/**
 * Runs the middleware on everything except Next.js internals and static files,
 * unless a search param is present — so server actions on static-looking paths
 * still pass through auth.
 */
export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};

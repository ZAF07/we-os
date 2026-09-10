import path from "node:path";

import { clerk, clerkSetup } from "@clerk/testing/playwright";
import { expect, test as setup } from "@playwright/test";

import { saveRenewableSession } from "./session-state";

// The two sign-ins must not overlap: run in parallel they race each other
// through Clerk's sign-in flow and both storage states come out wrong.
setup.describe.configure({ mode: "serial" });

/**
 * Signs in the suite's two test users and saves a session for each.
 *
 * Every route in the app half is behind `clerkMiddleware`, so the specs need
 * a real session.
 * This runs as a Playwright dependency project: it authenticates the dedicated
 * test users and writes the browser state the other projects reuse.
 *
 * There are two because the engine derives the tenant from the `org_id` claim
 * on the session token, so a second tenant means a second organization — and a
 * second dedicated user keeps that claim a fixed property of a saved storage
 * state rather than something a fixture has to switch and re-verify mid-run.
 * The seeded user's tenant carries a complete Brand DNA; the blank user's
 * carries none, which is what the onboarding specs need.
 *
 * Sign-in is by email address, which mints a sign-in ticket through Clerk's
 * Backend API. That means no test password exists to be stored, leaked, or
 * rejected by Clerk's breached-password check.
 */

export const STORAGE_STATE = path.join(__dirname, "../.auth/user.json");
export const BLANK_STORAGE_STATE = path.join(
  __dirname,
  "../.auth/blank-user.json",
);

/**
 * The routes the seeded specs hit, warmed once so no spec pays the first
 * compile.
 *
 * The dev server compiles a route the first time it is hit, and under parallel
 * load that first hit can outlast an assertion — a spec then fails on a slow
 * first paint rather than on anything the product did. Doing it once here,
 * serially, costs a few seconds and takes the whole class of flake off the
 * table.
 *
 * The Workspace and the run stream are reached only by a slug the seed cannot
 * know, so they are warmed with one that does not exist: the route compiles
 * the same whether it then renders a campaign or "not found". The Workspace is
 * the heaviest route there is — its client bundle carries the markdown
 * renderer — and every campaign-creating spec lands on it right after
 * "Create campaign", inside a 5 s assertion. Before it was listed here, the
 * first of them to arrive paid its compile, 3 s alone and up to 10 s under
 * parallel load, and a different spec failed each run depending on which one
 * got there first.
 */
const SEEDED_ROUTES = [
  "/campaigns",
  "/campaigns/new",
  "/calendar",
  "/brand",
  "/performance",
  "/onboarding",
  "/campaigns/warm-up-slug-that-does-not-exist",
  "/api/runs/warm-up-run-that-does-not-exist/stream",
];

/** The blank tenant's specs only ever leave `/onboarding` for `/brand`. */
const BLANK_ROUTES = ["/onboarding", "/brand"];

const IDENTITIES = [
  {
    name: "seeded",
    variable: "E2E_CLERK_USER_EMAIL",
    storageState: STORAGE_STATE,
    routes: SEEDED_ROUTES,
  },
  {
    name: "blank",
    variable: "E2E_CLERK_BLANK_USER_EMAIL",
    storageState: BLANK_STORAGE_STATE,
    routes: BLANK_ROUTES,
  },
];

for (const identity of IDENTITIES) {
  setup(`authenticate the ${identity.name} user`, async ({ page }) => {
    const email = process.env[identity.variable];

    if (!email) {
      throw new Error(
        `Set ${identity.variable} to a Clerk test user, in either ` +
          "web/.env.local or web/.env. See web/.env.local.example.",
      );
    }

    await clerkSetup();

    // clerk.signIn requires an already-loaded, unprotected page.
    await page.goto("/sign-in");
    await clerk.loaded({ page });
    await clerk.signIn({ page, emailAddress: email });

    await page.goto("/home");
    await expect(page).toHaveURL(/\/home$/);
    await expect(page.locator("aside").getByText("We-OS")).toBeVisible();

    await saveRenewableSession(page.context(), identity.storageState);

    for (const route of identity.routes) {
      await page.goto(route);
    }
  });
}

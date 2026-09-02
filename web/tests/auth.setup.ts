import path from "node:path";

import { clerk, clerkSetup } from "@clerk/testing/playwright";
import { expect, test as setup } from "@playwright/test";

/**
 * Signs in once and saves the session, so the feature specs run authenticated.
 *
 * Every route is behind `clerkMiddleware`, so the specs need a real session.
 * This runs as a Playwright dependency project: it authenticates a dedicated
 * test user and writes the browser state that the other projects reuse.
 *
 * Sign-in is by email address, which mints a sign-in ticket through Clerk's
 * Backend API. That means no test password exists to be stored, leaked, or
 * rejected by Clerk's breached-password check.
 */

export const STORAGE_STATE = path.join(__dirname, "../.auth/user.json");

setup("authenticate", async ({ page }) => {
  const email = process.env.E2E_CLERK_USER_EMAIL;

  if (!email) {
    throw new Error(
      "Set E2E_CLERK_USER_EMAIL to a Clerk test user, in either web/.env.local " +
        "or web/.env. See web/.env.local.example.",
    );
  }

  await clerkSetup();

  // clerk.signIn requires an already-loaded, unprotected page.
  await page.goto("/sign-in");
  await clerk.loaded({ page });
  await clerk.signIn({ page, emailAddress: email });

  await page.goto("/");
  await expect(page).toHaveURL(/^(?!.*\/sign-in).*$/);
  await expect(page.locator("aside").getByText("Marketing OS")).toBeVisible();

  await page.context().storageState({ path: STORAGE_STATE });
});

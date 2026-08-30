import path from "node:path";

import { clerk, clerkSetup } from "@clerk/testing/playwright";
import { expect, test as setup } from "@playwright/test";

/**
 * Signs in once and saves the session, so the feature specs run authenticated.
 *
 * Every route is behind `clerkMiddleware`, so the specs need a real session.
 * This runs as a Playwright dependency project: it authenticates a dedicated
 * test user and writes the browser state that the other projects reuse.
 */

export const STORAGE_STATE = path.join(__dirname, "../.auth/user.json");

setup("authenticate", async ({ page }) => {
  const email = process.env.E2E_CLERK_USER_EMAIL;
  const password = process.env.E2E_CLERK_USER_PASSWORD;

  if (!email || !password) {
    throw new Error(
      "Set E2E_CLERK_USER_EMAIL and E2E_CLERK_USER_PASSWORD in web/.env.local " +
        "to a Clerk test user. See .env.local.example.",
    );
  }

  await clerkSetup();
  await page.goto("/sign-in");
  await clerk.signIn({
    page,
    signInParams: { strategy: "password", identifier: email, password },
  });

  await page.goto("/");
  await expect(page.locator("aside").getByText("Marketing OS")).toBeVisible();
  await page.context().storageState({ path: STORAGE_STATE });
});

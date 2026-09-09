import path from "node:path";

import { clerk, clerkSetup } from "@clerk/testing/playwright";
import { expect, test as setup } from "@playwright/test";

import { deleteOrganizationsOf } from "./clerk-backend";
import { TENANTLESS_EMAIL, TENANTLESS_SKIP_REASON } from "./tenantless-user";

/**
 * Signs in the tenantless user and saves a session that carries no business.
 *
 * Its own setup project, apart from the two signed-in identities, so the
 * tenantless project stands or falls alone. With no
 * `E2E_CLERK_TENANTLESS_USER_EMAIL` set the project is skipped and says so —
 * the user is provisioned by hand in the Clerk dashboard, and a suite that
 * turned red for everyone until that happened would gate unrelated work on it.
 * With the variable set, anything wrong fails loudly.
 *
 * The user must belong to no Organization: the whole project is about what a
 * session with no business can and cannot reach. A previous run that failed
 * before its teardown may have left one behind, so any the user belongs to
 * are deleted first — nothing but this suite ever creates them.
 */

export const TENANTLESS_STORAGE_STATE = path.join(
  __dirname,
  "../.auth/tenantless-user.json",
);

setup("authenticate the tenantless user", async ({ page }) => {
  setup.skip(!TENANTLESS_EMAIL, TENANTLESS_SKIP_REASON);
  const email = TENANTLESS_EMAIL ?? "";

  await clerkSetup();
  await deleteOrganizationsOf(email);

  await page.goto("/sign-in");
  await clerk.loaded({ page });
  await clerk.signIn({ page, emailAddress: email });

  // With Clerk's organization-on-sign-up setting still on, a person with no
  // organization is held in a "pending" session and never reaches the app —
  // the welcome flow cannot run, and the failure would otherwise look like a
  // redirect to the wrong place.
  const status = await page.evaluate(
    () =>
      (window as unknown as { Clerk?: { session?: { status?: string } } }).Clerk
        ?.session?.status,
  );
  expect(
    status,
    "the tenantless user's session must be active: turn off Clerk's " +
      "organization requirement on sign-up (see web/README.md)",
  ).toBe("active");

  // The gate is the first assertion: signed in with no business, Home is not
  // reachable, and the way forward is to choose a tier.
  await page.goto("/home");
  await expect(page).toHaveURL("/get-started");

  await page.context().storageState({ path: TENANTLESS_STORAGE_STATE });
});

import path from "node:path";

import { clerk, clerkSetup } from "@clerk/testing/playwright";
import { expect, test as setup } from "@playwright/test";

import {
  allowOrganizationCreationFor,
  deleteOrganizationsOf,
} from "./clerk-backend";
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
 * are deleted first — nothing but this suite ever creates them. The user must
 * also be allowed to create one, which Clerk decides per user from the
 * instance default in force when the user was created; a user created before
 * that default was turned on is repaired here, and the repair is announced so
 * the instance default gets a second look — every real sign-up depends on it.
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
  if (await allowOrganizationCreationFor(email)) {
    console.log(
      `Turned on "create organizations" for ${email}. Check that the Clerk ` +
        'instance\'s "allow users to create organizations" default is on too, ' +
        "or real sign-ups will fail at Welcome the same way.",
    );
  }

  await page.goto("/sign-in");
  await clerk.loaded({ page });
  await clerk.signIn({ page, emailAddress: email });

  // While the Clerk instance requires organization membership, a person with
  // no organization is held in a "pending" session on a "choose-organization"
  // task and never reaches the app — the welcome flow cannot run, and the
  // failure would otherwise look like a redirect to the wrong place. Naming
  // the task and the setting beats a bare status mismatch.
  const session = await page.evaluate(() => {
    const { Clerk } = window as unknown as {
      Clerk?: { session?: { status?: string; currentTask?: { key?: string } } };
    };
    return {
      status: Clerk?.session?.status,
      task: Clerk?.session?.currentTask?.key,
    };
  });
  expect(
    session.status,
    `the tenantless user's session is "${session.status}"` +
      (session.task ? ` on the "${session.task}" task` : "") +
      ", not active. In the Clerk Dashboard, under Organizations settings, " +
      'switch "Membership required" to "Membership optional" (Personal ' +
      "Accounts on): required membership makes Clerk demand an organization " +
      "after sign-in, and the welcome flow never runs. See web/README.md.",
  ).toBe("active");

  // The gate is the first assertion: signed in with no business, Home is not
  // reachable, and the way forward is to choose a tier.
  await page.goto("/home");
  await expect(page).toHaveURL("/get-started");

  await page.context().storageState({ path: TENANTLESS_STORAGE_STATE });
});

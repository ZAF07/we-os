import { clerk } from "@clerk/testing/playwright";
import { expect, test, type Page, type Response } from "@playwright/test";

import { createOrganizationFor, deleteOrganizationsOf } from "./clerk-backend";
import { uniqueName } from "./fixtures";
import { TENANTLESS_EMAIL, TENANTLESS_SKIP_REASON } from "./tenantless-user";

// Every spec here ends by making the user tenantless again, and two of them
// create a business, so they run one at a time in declaration order.
test.describe.configure({ mode: "serial" });

// Skipped, and reported as such, until the tenantless user is provisioned.
test.skip(!TENANTLESS_EMAIL, TENANTLESS_SKIP_REASON);

/**
 * The gate and the welcome flow, as a person who has just signed up.
 *
 * Nothing below the browser can prove that a session with no business cannot
 * reach Home, so these open the app the way a new person would — with a real
 * session that carries no organization — and check where they land. Each
 * spec leaves the user as it found them: the Organizations a spec creates are
 * deleted through Clerk's Backend API afterwards, so the fixture is tenantless
 * for the next run.
 */

const EMAIL = TENANTLESS_EMAIL ?? "";

const APP_ROUTES = [
  "/home",
  "/campaigns",
  "/calendar",
  "/brand",
  "/performance",
  "/onboarding",
];

/**
 * Lists the app paths a navigation passed through, from the one requested to
 * the one that answered.
 *
 * Only the app's own addresses: on a development instance Clerk may bounce a
 * request through its handshake endpoint to refresh the session, and that hop
 * says nothing about where the app sent the person.
 *
 * Args:
 *   response: The response `page.goto` resolved with.
 *
 * Returns:
 *   The paths, earliest first.
 */
function redirectPath(response: Response | null): string[] {
  const paths: string[] = [];
  let request = response?.request() ?? null;
  while (request) {
    const url = new URL(request.url());
    if (url.hostname === "localhost") paths.unshift(url.pathname);
    request = request.redirectedFrom();
  }
  return paths;
}

/**
 * Activates an Organization on the browser's session, as Welcome does.
 *
 * Args:
 *   page: A page on which Clerk has loaded.
 *   organizationId: The Organization to activate.
 */
async function activateOrganization(page: Page, organizationId: string) {
  await clerk.loaded({ page });
  await page.evaluate(async (id) => {
    const { Clerk } = window as unknown as {
      Clerk: {
        setActive: (params: { organization: string | null }) => Promise<void>;
      };
    };
    await Clerk.setActive({ organization: id });
  }, organizationId);
}

test.afterEach(async () => {
  await deleteOrganizationsOf(EMAIL);
});

test("a session with no business is sent from every route in the app half to Welcome", async ({
  page,
}) => {
  for (const route of APP_ROUTES) {
    const response = await page.goto(route);

    // Welcome then sends a person with no tier to choose one, so the gate is
    // seen in the redirect chain rather than in the page that answers.
    expect(redirectPath(response), `redirects from ${route}`).toContain(
      "/welcome",
    );
    await expect(page).toHaveURL("/get-started");
  }
});

test("Welcome with no tier, or a tier that does not exist, sends the person to choose one", async ({
  page,
}) => {
  await page.goto("/welcome");
  await expect(page).toHaveURL("/get-started");
  await expect(
    page.getByRole("heading", { name: "Choose your tier." }),
  ).toBeVisible();

  await page.goto("/welcome?tier=platinum");
  await expect(page).toHaveURL("/get-started");
});

test("Launch on Get Started leads a signed-in person to Welcome, not to a sign-up form", async ({
  page,
}) => {
  await page.goto("/get-started");

  for (const [name, param] of [
    ["Operator", "operator"],
    ["Strategist", "strategist"],
    ["Command", "command"],
  ]) {
    await expect(
      page.getByRole("article", { name }).getByRole("link", { name: "Launch" }),
    ).toHaveAttribute("href", `/welcome?tier=${param}`);
  }
});

test("a business whose tier was never recorded is sent from Home to choose, and Launch finishes it", async ({
  page,
}) => {
  // The one state the Home check exists for: an Organization active on the
  // session, and a tenant with no tier because the tier call never ran. The
  // app never leaves a business like this on purpose, so it is built around
  // it — the Organization through the Backend API, the activation as Welcome
  // would do it.
  const organizationId = await createOrganizationFor(
    EMAIL,
    uniqueName("Tierless"),
  );
  await page.goto("/get-started");
  await activateOrganization(page, organizationId);

  // Straight to Get Started: bare Welcome would send a session that already
  // has a business back to Home.
  const response = await page.goto("/home");
  expect(redirectPath(response)).not.toContain("/welcome");
  await expect(page).toHaveURL("/get-started");

  await page
    .getByRole("article", { name: "Strategist" })
    .getByRole("link", { name: "Launch" })
    .click();
  await expect(page).toHaveURL("/welcome?tier=strategist");
  await expect(page).toHaveURL("/home", { timeout: 60_000 });
  await expect(page.getByRole("heading", { name: "Home" })).toBeVisible();
});

test("naming the business at Welcome creates it, records the tier, and lands on Home", async ({
  page,
}) => {
  const name = uniqueName("Coast Coffee");

  await page.goto("/welcome?tier=command");
  await expect(
    page.getByRole("heading", { name: "Name your business." }),
  ).toBeVisible();
  await expect(page.getByText("You chose the Command tier.")).toBeVisible();
  // Nothing to navigate yet: no rail, no product.
  await expect(page.locator("aside")).toHaveCount(0);

  await page.getByLabel("Business name").fill(name);
  await page.getByRole("button", { name: "Create my business" }).click();

  await expect(page).toHaveURL("/home", { timeout: 60_000 });
  await expect(page.getByRole("heading", { name: "Home" })).toBeVisible();
  await expect(page.locator("aside").getByText(name)).toBeVisible();
});

import { expect, test } from "@playwright/test";

import { uniqueName } from "./fixtures";

const NAV_ROUTES: Array<{ label: string; path: string }> = [
  { label: "Campaigns", path: "/campaigns" },
  { label: "Calendar", path: "/calendar" },
  { label: "Brand", path: "/brand" },
  { label: "Performance", path: "/performance" },
  { label: "Home", path: "/" },
];

test("nav rail reaches every primary route and marks it active", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.locator("aside").getByText("Marketing OS")).toBeVisible();

  // Scoped to the rail: the screens themselves link to each other now that
  // their empty states point somewhere useful, so a bare name matches more than
  // the nav item this is about.
  const rail = page.locator("aside");
  for (const { label, path } of NAV_ROUTES) {
    const link = rail.getByRole("link", { name: label });
    await link.click();
    await expect(page).toHaveURL(path);
    await expect(link).toHaveAttribute("aria-current", "page");
  }
});

test("all routes resolve without a 404", async ({ page }) => {
  const paths = [
    "/",
    "/campaigns",
    "/campaigns/new",
    "/calendar",
    "/brand",
    "/performance",
    "/onboarding",
  ];
  for (const path of paths) {
    const response = await page.goto(path);
    expect(response, `no response for ${path}`).not.toBeNull();
    expect(response!.status(), `status for ${path}`).toBe(200);
  }
});

test("workspace route highlights the Campaigns nav item", async ({ page }) => {
  await page.goto("/campaigns/fernway-refill-launch");
  await expect(
    page.locator("aside").getByRole("link", { name: "Campaigns" }),
  ).toHaveAttribute("aria-current", "page");
});

test("below the mobile breakpoint the nav collapses into a drawer", async ({
  page,
}) => {
  await page.setViewportSize({ width: 375, height: 720 });
  await page.goto("/");
  await expect(
    page.locator("aside").getByRole("link", { name: "Campaigns" }),
  ).toBeHidden();

  await page.getByRole("button", { name: "Open navigation" }).click();
  await page
    .getByRole("navigation")
    .getByRole("link", { name: "Campaigns" })
    .click();
  await expect(page).toHaveURL("/campaigns");

  const overflowX = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth,
  );
  expect(overflowX).toBe(false);
});

test("the create-campaign path works end to end", async ({ page }) => {
  const name = uniqueName("Smoke Campaign");

  await page.goto("/campaigns");
  await page.getByRole("link", { name: "New campaign" }).click();

  await page.getByLabel("Campaign name").fill(name);
  await page
    .getByLabel("Primary business objective")
    .fill("40 new memberships in 8 weeks");
  await page.getByRole("button", { name: "Next →" }).click();

  await page.getByLabel("Business KPI").fill("40 memberships");
  await page.getByLabel("Marketing KPI").fill("3% landing-page conversion");
  await page.getByLabel("Creative KPI").fill("25% hook rate");
  await page.getByRole("button", { name: "Next →" }).click();

  await page.getByRole("radio").first().click();
  await page.getByLabel("Campaign budget").fill("3000");
  await page.getByLabel("Start date").fill("2026-09-01");
  await page.getByLabel("End date").fill("2026-10-27");
  await page.getByRole("button", { name: "Next →" }).click();

  await page.getByRole("button", { name: "Create campaign" }).click();
  await expect(page).toHaveURL(/\/campaigns\/smoke-campaign/);
  await expect(page.getByText(name)).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Stages" })).toBeVisible();

  await page.goto("/campaigns");
  await expect(page.getByText(name)).toBeVisible();
});

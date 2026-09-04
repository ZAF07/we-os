import { expect, test } from "@playwright/test";

/**
 * The table renders the tenant's real campaigns, so these assert on structure
 * and on the lifecycle behaviour — an archived campaign leaving the list —
 * rather than on fixture names that no longer exist.
 */
test("the campaigns table renders with its columns", async ({ page }) => {
  await page.goto("/campaigns");

  await expect(page.getByRole("heading", { name: "Campaigns" })).toBeVisible();
  for (const column of ["Campaign", "Stage", "Status", "Next action"]) {
    await expect(page.getByText(column, { exact: true })).toBeVisible();
  }
});

test("the New campaign button navigates to the wizard route", async ({
  page,
}) => {
  await page.goto("/campaigns");
  await page.getByRole("link", { name: "New campaign" }).click();
  await expect(page).toHaveURL("/campaigns/new");
});

test("a campaign can be archived and leaves the active list", async ({
  page,
}) => {
  const name = `Archivable ${Date.now()}`;

  await page.goto("/campaigns/new");
  await page.getByLabel("Campaign name").fill(name);
  await page.getByLabel("Primary business objective").fill("An objective");
  await page.getByRole("button", { name: "Next →" }).click();
  await page.getByLabel("Business KPI").fill("A business target");
  await page.getByLabel("Marketing KPI").fill("A marketing target");
  await page.getByLabel("Creative KPI").fill("A creative target");
  await page.getByRole("button", { name: "Next →" }).click();
  await page.getByRole("radio").first().click();
  await page.getByLabel("Campaign budget").fill("1000");
  await page.getByLabel("Start date").fill("2026-09-01");
  await page.getByLabel("End date").fill("2026-10-27");
  await page.getByRole("button", { name: "Next →" }).click();
  await page.getByRole("button", { name: "Create campaign" }).click();
  await expect(page).toHaveURL(/\/campaigns\/archivable/);
  await expect(page.getByRole("navigation", { name: "Stages" })).toBeVisible();

  await page.goto("/campaigns");
  await expect(page.getByText(name)).toBeVisible();

  await page.getByRole("button", { name: `Archive ${name}` }).click();
  await expect(page.getByText(name)).toHaveCount(0);
});

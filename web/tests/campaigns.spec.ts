import { expect, test } from "@playwright/test";

test("campaigns table renders every fixture row", async ({ page }) => {
  await page.goto("/campaigns");

  await expect(page.getByRole("heading", { name: "Campaigns" })).toBeVisible();

  for (const name of [
    "Fernway Refill Launch",
    "Summer Refill Drop",
    "Loyalty Newsletter",
    "Earth Month Retargeting",
  ]) {
    await expect(page.getByText(name, { exact: true })).toBeVisible();
  }

  await expect(page.getByText("Acquisition · Q3 hero")).toBeVisible();
  await expect(page.getByText("3/8")).toBeVisible();
  await expect(page.getByText("Ready for review").first()).toBeVisible();
  await expect(page.getByText("Approve audience & positioning")).toBeVisible();
  await expect(page.getByText("2h ago")).toBeVisible();
});

test("clicking a campaign row opens its workspace", async ({ page }) => {
  await page.goto("/campaigns");
  await page.getByText("Summer Refill Drop", { exact: true }).click();
  await expect(page).toHaveURL("/campaigns/summer-refill-drop");
});

test("the New campaign button navigates to the wizard route", async ({
  page,
}) => {
  await page.goto("/campaigns");
  await page.getByRole("link", { name: "New campaign" }).click();
  await expect(page).toHaveURL("/campaigns/new");
});

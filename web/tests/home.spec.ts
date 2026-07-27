import { expect, test } from "@playwright/test";

test("home renders its headline sections from fixtures", async ({ page }) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: "Good morning, Maya" }),
  ).toBeVisible();

  for (const label of [
    "Pending approvals",
    "Active campaigns",
    "Scheduled this week",
    "Blocked",
  ]) {
    await expect(page.getByText(label, { exact: true }).first()).toBeVisible();
  }
  await expect(page.getByText("Pending approvals")).toBeVisible();

  await expect(page.getByText("Action queue")).toBeVisible();
  await expect(page.getByText("In progress now")).toBeVisible();
  await expect(page.getByText("Performance · 28 days")).toBeVisible();
  await expect(page.getByText("Scheduled next")).toBeVisible();
  await expect(page.getByText("Recent findings")).toBeVisible();
  await expect(page.getByText("Recommended next")).toBeVisible();

  await expect(page.getByText("Approve audience & positioning")).toBeVisible();
  await expect(page.getByText("4 items need you")).toBeVisible();
  await expect(page.getByText("Fernway Refill Launch").first()).toBeVisible();
  await expect(page.getByText("Earth Month Retargeting").first()).toBeVisible();
});

test("a decision queue CTA navigates to the campaign workspace", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Review" }).first().click();
  await expect(page).toHaveURL("/campaigns/fernway-refill-launch");
});

test("the flagged-claim CTA navigates to Brand", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Resolve" }).click();
  await expect(page).toHaveURL("/brand");
});

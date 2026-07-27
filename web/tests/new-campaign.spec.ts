import { expect, test } from "@playwright/test";

test("validation blocks the wizard until required inputs are filled", async ({
  page,
}) => {
  await page.goto("/campaigns/new");

  await expect(page.getByText("Step 1 of 6")).toBeVisible();
  await page.getByRole("button", { name: "Next →" }).click();
  await expect(
    page.getByText("Fill in the required fields to continue."),
  ).toBeVisible();
  await expect(page.getByText("Step 1 of 6")).toBeVisible();
});

test("completing the wizard creates the campaign and opens its Workspace at Brief", async ({
  page,
}) => {
  await page.goto("/campaigns");
  await page.getByRole("link", { name: "New campaign" }).click();
  await expect(page).toHaveURL("/campaigns/new");

  await page.getByLabel("Campaign name").fill("Autumn Referral Push");
  await page
    .getByLabel("What are we promoting, and why now?")
    .fill("Referral program relaunch ahead of the fall gifting season.");
  await page.getByLabel("Campaign owner & approver").fill("Maya Chen");
  await page.getByRole("button", { name: "Next →" }).click();

  await expect(page.getByText("Step 2 of 6")).toBeVisible();
  await page.getByLabel("Primary business objective").click();
  await page
    .getByRole("option", { name: "Improve customer retention" })
    .click();
  await page.getByLabel("Desired customer action").click();
  await page.getByRole("option", { name: "Subscribe" }).click();
  await page
    .getByLabel("Primary success metric")
    .fill("1,000 referral signups by Sep 30");
  await page.getByRole("button", { name: "Next →" }).click();

  await expect(page.getByText("Step 3 of 6")).toBeVisible();
  await expect(
    page.getByRole("radio", { name: "Design-led shoppers" }),
  ).toBeVisible();
  await page
    .getByRole("radio", { name: "Low-waste households (28–45)" })
    .click();
  await page.getByLabel("Funnel stage").click();
  await page.getByRole("option", { name: "Retention" }).click();
  await page.getByRole("button", { name: "Next →" }).click();

  await expect(page.getByText("Step 4 of 6")).toBeVisible();
  await page
    .getByLabel("Offer being promoted")
    .fill("Give $10, get $10 refill credit");
  await page.getByLabel("Primary call to action").fill("Refer a friend");
  await page.getByLabel("Total budget").fill("$12k");
  await page.getByLabel("Start date").fill("2026-08-01");
  await page.getByLabel("End date").fill("2026-09-15");
  await page.getByRole("button", { name: "Next →" }).click();

  await expect(page.getByText("Step 5 of 6")).toBeVisible();
  await page.getByRole("button", { name: "Next →" }).click();
  await expect(
    page.getByText("Select at least one channel to continue."),
  ).toBeVisible();
  await page.getByLabel("Email", { exact: true }).click();
  await page.getByLabel("Instagram", { exact: true }).click();
  await page.getByRole("button", { name: "Next →" }).click();

  await expect(page.getByText("Step 6 of 6")).toBeVisible();
  await expect(page.getByText("Autumn Referral Push")).toBeVisible();
  await expect(page.getByText("Improve customer retention")).toBeVisible();
  await expect(
    page.getByText("Low-waste households (28–45) · Retention"),
  ).toBeVisible();
  await expect(page.getByText("$12k")).toBeVisible();
  await page.getByRole("button", { name: "Create campaign" }).click();

  await expect(page).toHaveURL("/campaigns/autumn-referral-push");
  await expect(
    page.getByRole("heading", { name: "Campaign brief" }),
  ).toBeVisible();
  await expect(page.getByText("Give $10, get $10 refill credit")).toBeVisible();
  await expect(page.getByText("Refer a friend")).toBeVisible();
  await expect(page.getByText("Email, Instagram")).toBeVisible();
  await expect(
    page.getByText(
      "Referral program relaunch ahead of the fall gifting season.",
    ),
  ).toBeVisible();

  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Campaign brief" }),
  ).toBeVisible();

  await page.goto("/campaigns");
  const newRow = page
    .locator("div")
    .filter({ hasText: /^Autumn Referral Push/ })
    .filter({ hasText: "1/8" })
    .first();
  await expect(newRow).toBeVisible();
  await expect(page.getByText("Review brief")).toBeVisible();
  await expect(page.getByText("Just now")).toBeVisible();
});

import { expect, test } from "@playwright/test";

import { uniqueName } from "./fixtures";

/**
 * The wizard creates a real campaign through the engine, so these assert on
 * what the engine actually requires: all three KPI tiers, a segment chosen
 * from the Brand DNA, and no channel question — channels are the performance
 * specialist's call at stage 4 (ADR-0016).
 */
const CAMPAIGN_NAME = uniqueName("Autumn Referral Push");

test("validation blocks the wizard until required inputs are filled", async ({
  page,
}) => {
  await page.goto("/campaigns/new");

  await expect(page.getByText("Step 1 of 4")).toBeVisible();
  await page.getByRole("button", { name: "Next →" }).click();
  await expect(
    page.getByText("Fill in the required fields to continue."),
  ).toBeVisible();
  await expect(page.getByText("Step 1 of 4")).toBeVisible();
});

test("the wizard never asks the business owner to pick channels", async ({
  page,
}) => {
  await page.goto("/campaigns/new");

  // What must not exist is a channel *question*. The wizard's own copy says "we
  // choose the channels later — that is our job, not yours", which is the
  // product making exactly this promise, so matching the bare word would fail on
  // the reassurance it should be checking for.
  for (const step of [1, 2, 3]) {
    await expect(page.getByLabel(/channel/i)).toHaveCount(0);
    await expect(page.getByRole("group", { name: /channel/i })).toHaveCount(0);
    if (step < 3) await page.getByRole("button", { name: "Next →" }).click();
  }
});

test("the wizard collects all three KPI tiers", async ({ page }) => {
  await page.goto("/campaigns/new");
  await page.getByLabel("Campaign name").fill(CAMPAIGN_NAME);
  await page
    .getByLabel("Primary business objective")
    .fill("120 refill subscriptions in 8 weeks");
  await page.getByRole("button", { name: "Next →" }).click();

  await expect(page.getByText("Step 2 of 4")).toBeVisible();
  await expect(page.getByLabel("Business KPI")).toBeVisible();
  await expect(page.getByLabel("Marketing KPI")).toBeVisible();
  await expect(page.getByLabel("Creative KPI")).toBeVisible();

  await page.getByRole("button", { name: "Next →" }).click();
  await expect(
    page.getByText("Fill in the required fields to continue."),
  ).toBeVisible();
});

test("completing the wizard creates a real campaign that appears in the list", async ({
  page,
}) => {
  await page.goto("/campaigns");
  await page.getByRole("link", { name: "New campaign" }).click();
  await expect(page).toHaveURL("/campaigns/new");

  await page.getByLabel("Campaign name").fill(CAMPAIGN_NAME);
  await page
    .getByLabel("Primary business objective")
    .fill("120 refill subscriptions in 8 weeks");
  await page.getByRole("button", { name: "Next →" }).click();

  await page.getByLabel("Business KPI").fill("120 refill subscriptions");
  await page.getByLabel("Marketing KPI").fill("2.5% landing-page conversion");
  await page.getByLabel("Creative KPI").fill("30% hook rate on launch video");
  await page.getByRole("button", { name: "Next →" }).click();

  await expect(page.getByText("Step 3 of 4")).toBeVisible();
  const segment = page.getByRole("radio").first();
  await expect(segment).toBeVisible();
  const segmentName = (await segment.textContent()) ?? "";
  await segment.click();
  await page.getByLabel("Campaign budget").fill("4000");
  await page.getByLabel("Start date").fill("2026-09-01");
  await page.getByLabel("End date").fill("2026-10-27");
  await page.getByRole("button", { name: "Next →" }).click();

  await expect(page.getByText("Step 4 of 4")).toBeVisible();
  await expect(page.getByText(CAMPAIGN_NAME)).toBeVisible();
  await expect(
    page.getByText("120 refill subscriptions").first(),
  ).toBeVisible();
  await expect(page.getByText(segmentName.trim())).toBeVisible();
  await page.getByRole("button", { name: "Create campaign" }).click();

  await expect(page).toHaveURL(/\/campaigns\/autumn-referral-push/);
  await expect(page.getByText(CAMPAIGN_NAME)).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Stages" })).toBeVisible();

  await page.goto("/campaigns");
  await expect(page.getByText(CAMPAIGN_NAME)).toBeVisible();
});

test("the target segment is chosen from the Brand DNA, not typed", async ({
  page,
}) => {
  await page.goto("/campaigns/new");
  await page.getByLabel("Campaign name").fill(CAMPAIGN_NAME);
  await page.getByLabel("Primary business objective").fill("An objective");
  await page.getByRole("button", { name: "Next →" }).click();
  await page.getByLabel("Business KPI").fill("A business target");
  await page.getByLabel("Marketing KPI").fill("A marketing target");
  await page.getByLabel("Creative KPI").fill("A creative target");
  await page.getByRole("button", { name: "Next →" }).click();

  await expect(page.getByRole("radiogroup")).toBeVisible();
  await expect(page.getByRole("radio").first()).toBeVisible();
});

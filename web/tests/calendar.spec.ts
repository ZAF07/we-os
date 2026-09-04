import { expect, test } from "@playwright/test";

/**
 * Calendar shows real campaign timeframes. Publishing arrives in a later PRD,
 * so it must not fabricate post schedules — these assert both that real
 * timeframes render and that invented ones do not.
 */

test("calendar renders planned timeframes", async ({ page }) => {
  await page.goto("/calendar");

  await expect(page.getByRole("heading", { name: "Calendar" })).toBeVisible();
  await expect(
    page.getByText(/When each campaign is planned to run/),
  ).toBeVisible();
});

test("it is explicit that per-post scheduling does not exist yet", async ({
  page,
}) => {
  await page.goto("/calendar");

  const empty = page.getByText("Nothing scheduled");
  if (await empty.isVisible()) {
    await expect(page.getByText(/Campaigns appear here/)).toBeVisible();
  } else {
    await expect(page.getByText("Planned timeframes")).toBeVisible();
    await expect(page.getByText(/Not here yet:/)).toBeVisible();
  }
});

test("a created campaign appears with its real timeframe", async ({ page }) => {
  const name = `Calendar ${Date.now()}`;

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
  await expect(page.getByRole("navigation", { name: "Stages" })).toBeVisible();

  await page.goto("/calendar");
  await expect(page.getByText(name)).toBeVisible();
});

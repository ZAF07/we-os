import { expect, test } from "@playwright/test";

/**
 * Performance reports the *plan*, not measured results — nothing has been
 * published, so there is nothing to measure. These assert that the screen is
 * honest about that, and that it renders a real Performance Plan when one
 * exists rather than fixture metrics.
 */

test("performance says plainly that these are plans, not measurements", async ({
  page,
}) => {
  await page.goto("/performance");

  await expect(
    page.getByRole("heading", { name: "Performance" }),
  ).toBeVisible();
  await expect(
    page.getByText(/These are decisions, not\s+measurements/),
  ).toBeVisible();
});

test("with no plan yet, it names what will fill the screen", async ({
  page,
}) => {
  await page.goto("/performance");

  const empty = page.getByText("Nothing planned yet");
  if (await empty.isVisible()) {
    await expect(
      page.getByText(/channel mix|Plan stage/).first(),
    ).toBeVisible();
  } else {
    // A plan exists, so the screen must be showing its content.
    await expect(
      page.getByLabel(/^Performance plan for /).first(),
    ).toBeVisible();
  }
});

test("it invents no measured metrics", async ({ page }) => {
  await page.goto("/performance");

  // The old fixture screen showed a 28-day results dashboard. Nothing may
  // report measurements until publishing exists.
  await expect(page.getByText("28 days", { exact: true })).toHaveCount(0);
  await expect(page.getByText("What happened", { exact: true })).toHaveCount(0);
});

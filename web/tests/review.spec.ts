import { expect, test } from "@playwright/test";

/**
 * The platform asks the business to look at its Brand DNA again on an interval
 * (ADR-0028). The seed places the test tenant's last review a month back, so a
 * review is due from the first request — and the e2e engine runs on a 20 s
 * interval, so it is due again 20 s after anything clears it.
 *
 * Clearing is the wrinkle. Saving any answer counts as a review, and the brand
 * and clarification specs save answers to this same tenant while this one
 * runs. So neither half asserts on a single read: each polls until the review
 * is due, which the short interval guarantees within a minute, and the walk
 * from Reviewed back to Home fits well inside the interval that follows.
 */

const DUE_AGAIN = { timeout: 90_000, intervals: [3_000] };

test("a due Brand DNA review reaches Home, and the Brand page's Reviewed action clears it", async ({
  page,
}) => {
  const queue = page.getByRole("list", { name: "Decision queue" });
  const row = queue
    .locator("li")
    .filter({ hasText: "Your Brand DNA is due a review" });

  // Home derives the queue from the same read the engine makes, so the due
  // review is on it — tagged Review in amber, and leading to the Brand page.
  await expect(async () => {
    await page.goto("/home");
    await expect(row).toBeVisible({ timeout: 2_000 });
  }).toPass(DUE_AGAIN);
  await expect(row.getByText("Review", { exact: true }).first()).toHaveClass(
    /text-amber-800/,
  );
  await expect(row).toContainText("Last reviewed");

  await row.getByRole("link", { name: "Review" }).click();
  await expect(page).toHaveURL(/\/brand$/);

  // The Brand page asks for the look and offers Reviewed. Polled for the same
  // reason as above: another spec's save may have cleared it on the way here.
  const banner = page.getByRole("region", { name: "Brand DNA review" });
  await expect(async () => {
    await page.reload();
    await expect(banner).toBeVisible({ timeout: 2_000 });
  }).toPass(DUE_AGAIN);

  await banner.getByRole("button", { name: "Reviewed" }).click();
  await expect(banner).toBeHidden({ timeout: 30_000 });

  // Marked just now, so Home no longer asks — the item was derived, not stored.
  await page.goto("/home");
  await expect(row).toHaveCount(0);
});

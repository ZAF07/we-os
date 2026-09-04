import { expect, test } from "@playwright/test";

/**
 * Brand renders the tenant's real Brand DNA — the answers the business gave to
 * the published questionnaire — and edits them in place. So these assert on the
 * seeded business's own answers, which the e2e stack fixes deliberately for
 * exactly this reason.
 */

const SEEDED_BUSINESS = "Summit Climbing Collective";

test("brand renders the questionnaire's sections and the business's answers", async ({
  page,
}) => {
  await page.goto("/brand");

  const index = page.getByRole("navigation", { name: "Brand sections" });
  await expect(index.getByRole("button", { name: /Business/ })).toBeVisible();
  await expect(index.getByRole("button", { name: /Customers/ })).toBeVisible();

  await expect(page.getByText(SEEDED_BUSINESS).first()).toBeVisible();
});

test("completeness is stated plainly, not implied", async ({ page }) => {
  await page.goto("/brand");

  await expect(
    page.getByText(/Required answers are in|Every Required answer is in/),
  ).toBeVisible();
});

test("switching section shows that section's questions", async ({ page }) => {
  await page.goto("/brand");

  const index = page.getByRole("navigation", { name: "Brand sections" });
  await index.getByRole("button", { name: /Customers/ }).click();

  await expect(page.getByRole("heading", { name: "Customers" })).toBeVisible();
});

test("an individual answer can be edited and saved", async ({ page }) => {
  await page.goto("/brand");

  // Where the business serves customers is a single-line answer no other spec
  // asserts on, so editing it cannot disturb the segments the campaign specs
  // pick from.
  const index = page.getByRole("navigation", { name: "Brand sections" });
  await index.getByRole("button", { name: /Reach/ }).click();

  await page
    .getByRole("button", { name: "Edit: Where do you serve customers?" })
    .click();

  const updated = `Singapore, edited ${Date.now()}`;
  await page.getByLabel("Where do you serve customers?").fill(updated);
  await page.getByRole("button", { name: "Save", exact: true }).click();

  await expect(page.getByText(updated)).toBeVisible({ timeout: 30_000 });
});

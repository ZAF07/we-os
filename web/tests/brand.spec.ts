import { expect, test } from "@playwright/test";

import { uniqueName } from "./fixtures";

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

  const updated = uniqueName("Singapore, edited");
  await page.getByLabel("Where do you serve customers?").fill(updated);
  await page.getByRole("button", { name: "Save", exact: true }).click();

  await expect(page.getByText(updated)).toBeVisible({ timeout: 30_000 });
});

test("a blank answer is refused rather than saved as an empty one", async ({
  page,
}) => {
  await page.goto("/brand");

  const index = page.getByRole("navigation", { name: "Brand sections" });
  await index.getByRole("button", { name: /Reach/ }).click();

  await page
    .getByRole("button", {
      name: "Edit: What languages do your customers speak?",
    })
    .click();
  await page.getByLabel("What languages do your customers speak?").fill("  ");
  await page.getByRole("button", { name: "Save", exact: true }).click();

  await expect(
    page.getByText("An answer cannot be blank.", { exact: false }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Save", exact: true }),
  ).toBeVisible();
});

test("an answer can be deleted, and the question goes back to unanswered", async ({
  page,
}) => {
  // Competitors is Recommended and unseeded, so this spec answers it and then
  // withdraws it — leaving the shared test tenant exactly as it found it, and
  // never taking a Required answer out from under another spec's gate.
  await page.goto("/brand");

  const index = page.getByRole("navigation", { name: "Brand sections" });
  await index.getByRole("button", { name: /Recommended/ }).click();

  const question = "Who do you lose deals to?";
  await page.getByRole("button", { name: `Edit: ${question}` }).click();
  const rival = uniqueName("Boulder Republic");
  await page.getByLabel(question).fill(rival);
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByText(rival)).toBeVisible({ timeout: 30_000 });

  await page
    .getByRole("button", { name: "Delete answer: Competitors" })
    .click();

  await expect(page.getByText(rival)).toBeHidden({ timeout: 30_000 });
  await expect(page.getByText("Not answered yet.").first()).toBeVisible();
});

test("deleting a Required answer flips the banner to name what is now owed", async ({
  page,
}) => {
  // Takes out a Required answer and puts it straight back, so the shared test
  // tenant ends as it started and no other spec finds the gate closed.
  await page.goto("/brand");

  const index = page.getByRole("navigation", { name: "Brand sections" });
  await index.getByRole("button", { name: /Reach/ }).click();

  await expect(page.getByText(/Every Required answer is in/)).toBeVisible();

  await page
    .getByRole("button", { name: "Delete answer: Language(s)" })
    .click();

  await expect(
    page.getByText(/Required answers are in\. Campaigns cannot run/),
  ).toBeVisible({ timeout: 30_000 });

  await page
    .getByRole("button", {
      name: "Edit: What languages do your customers speak?",
    })
    .click();
  await page
    .getByLabel("What languages do your customers speak?")
    .fill("English");
  await page.getByRole("button", { name: "Save", exact: true }).click();

  await expect(page.getByText(/Every Required answer is in/)).toBeVisible({
    timeout: 30_000,
  });
});

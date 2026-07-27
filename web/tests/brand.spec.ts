import { expect, test } from "@playwright/test";

const SECTION_NAMES = [
  "Positioning",
  "Products & services",
  "Audience segments",
  "Voice & tone",
  "Claims & evidence",
  "Visual identity",
  "Restricted language",
  "Competitors",
  "Approved examples",
];

test("brand renders the 9-section index and section entries", async ({
  page,
}) => {
  await page.goto("/brand");

  const index = page.getByRole("navigation", { name: "Brand sections" });
  for (const name of SECTION_NAMES) {
    await expect(index.getByRole("button", { name })).toBeVisible();
  }

  await expect(
    page.getByRole("heading", { name: "Positioning" }),
  ).toBeVisible();
  await expect(page.getByText("Last verified Jul 2")).toBeVisible();
  await expect(page.getByText("Category frame")).toBeVisible();
  await expect(
    page.getByText(
      "Used by 3 active campaigns. Changing this re-opens their Strategy stages.",
    ),
  ).toBeVisible();

  await index.getByRole("button", { name: "Competitors" }).click();
  await expect(
    page.getByRole("heading", { name: "Competitors" }),
  ).toBeVisible();
  await expect(page.getByText("Grove Collaborative")).toBeVisible();
});

test("restricted language renders warnings and pending-claim notes show", async ({
  page,
}) => {
  await page.goto("/brand");

  const index = page.getByRole("navigation", { name: "Brand sections" });
  await index.getByRole("button", { name: "Restricted language" }).click();
  await expect(page.getByText('"Non-toxic"')).toBeVisible();
  await expect(page.getByText("RESTRICTED").first()).toBeVisible();

  await index.getByRole("button", { name: "Claims & evidence" }).click();
  await expect(
    page.getByText("Currently blocking 1 asset in Summer Refill Drop."),
  ).toBeVisible();
});

test("home flagged-claim CTA deep-links to the Restricted language section", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Resolve" }).click();
  await expect(page).toHaveURL("/brand");
  await expect(
    page.getByRole("heading", { name: "Restricted language" }),
  ).toBeVisible();
  await expect(page.getByText('"Chemical-free"')).toBeVisible();
});

test("home attach-evidence CTA deep-links to Claims & evidence", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Attach evidence" }).click();
  await expect(page).toHaveURL("/brand");
  await expect(
    page.getByRole("heading", { name: "Claims & evidence" }),
  ).toBeVisible();
});

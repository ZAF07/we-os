import { expect, test } from "@playwright/test";

test("required-field validation blocks advancing past an incomplete step", async ({
  page,
}) => {
  await page.goto("/onboarding");

  await expect(page.getByText("Step 1 of 5")).toBeVisible();
  await expect(
    page.getByText("AI extraction from your documents isn't available yet"),
  ).toBeVisible();

  await page.getByRole("button", { name: "Next →" }).click();
  await expect(
    page.getByText("Fill in the required fields to continue."),
  ).toBeVisible();
  await expect(page.getByText("Step 1 of 5")).toBeVisible();
});

test("completing onboarding populates the Brand screen with entered data", async ({
  page,
}) => {
  await page.goto("/onboarding");

  await page.getByLabel("Company name").fill("Acme Coffee");
  await page
    .getByLabel("Company description")
    .fill("Specialty coffee kits for busy people.");
  await page.getByLabel("Industry & category").fill("Specialty coffee");
  await page
    .getByLabel("Products or services")
    .fill("Acme Brew Kit — dripper, filters and beans");
  await page.getByRole("button", { name: "Next →" }).click();

  await expect(page.getByText("Step 2 of 5")).toBeVisible();
  await page.getByLabel("Primary customer segment").fill("Urban commuters");
  await page
    .getByLabel("What defines them")
    .first()
    .fill("Grab coffee on the go, value speed over ritual.");
  await page
    .getByLabel("Customer problems & pain points")
    .fill("Long queues at cafes before work.");
  await page.getByRole("button", { name: "Next →" }).click();

  await expect(page.getByText("Step 3 of 5")).toBeVisible();
  await page
    .getByLabel("Core value proposition")
    .fill("Cafe-quality coffee in 90 seconds.");
  await page
    .getByLabel("Primary customer promise")
    .fill("Cafe taste without the queue.");
  await page
    .getByLabel("Key differentiators")
    .fill("Patented 90-second brew method.");
  await page
    .getByLabel("Main competitors")
    .fill("Blue Bottle — we win on speed");
  await page.getByRole("button", { name: "Next →" }).click();

  await expect(page.getByText("Step 4 of 5")).toBeVisible();
  await page.getByLabel("Brand personality").fill("Energetic and direct");
  await page.getByLabel("Tone of voice").fill("Snappy, friendly, concrete.");
  await page.getByRole("button", { name: "Next →" }).click();

  await expect(page.getByText("Step 5 of 5")).toBeVisible();
  await page
    .getByLabel("Restricted claims & terminology")
    .fill('"world\'s best" — unverifiable superlative');
  await page.getByRole("button", { name: "Finish onboarding" }).click();

  await expect(page).toHaveURL("/brand");
  await expect(
    page.getByRole("heading", { name: "Positioning" }),
  ).toBeVisible();
  await expect(
    page.getByText("Cafe-quality coffee in 90 seconds."),
  ).toBeVisible();
  await expect(page.getByText("Cafe taste without the queue.")).toBeVisible();
  await expect(page.getByText("Last verified Just now")).toBeVisible();

  const index = page.getByRole("navigation", { name: "Brand sections" });
  await index.getByRole("button", { name: "Audience segments" }).click();
  await expect(page.getByText("1 · Urban commuters")).toBeVisible();
  await expect(
    page.getByText("Grab coffee on the go, value speed over ritual."),
  ).toBeVisible();

  await index.getByRole("button", { name: "Voice & tone" }).click();
  await expect(page.getByText("Snappy, friendly, concrete.")).toBeVisible();

  await index.getByRole("button", { name: "Restricted language" }).click();
  await expect(page.getByText('"world\'s best"')).toBeVisible();
  await expect(page.getByText("RESTRICTED").first()).toBeVisible();

  await index.getByRole("button", { name: "Competitors" }).click();
  await expect(page.getByText("Blue Bottle")).toBeVisible();

  await expect(page.getByText("Acme Coffee workspace")).toBeVisible();

  await page.reload();
  await expect(page.getByText("Acme Coffee workspace")).toBeVisible();
  await expect(page.getByText("Blue Bottle")).toBeVisible();
  await index.getByRole("button", { name: "Positioning" }).click();
  await expect(
    page.getByText("Cafe-quality coffee in 90 seconds."),
  ).toBeVisible();
});

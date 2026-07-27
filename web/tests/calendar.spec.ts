import { expect, test } from "@playwright/test";

test("month grid places items on their days and highlights today", async ({
  page,
}) => {
  await page.goto("/calendar");

  await expect(
    page.getByRole("heading", { name: "Content · July 2026" }),
  ).toBeVisible();

  await expect(
    page.getByRole("button", { name: "Refill in 15 seconds" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Cost-per-clean math" }),
  ).toBeVisible();

  const today = page.getByText("16", { exact: true }).first();
  await expect(today).toHaveClass(/bg-primary/);
});

test("selecting an item shows its full detail", async ({ page }) => {
  await page.goto("/calendar");

  await expect(page.getByText("Reel · Refill in 15 seconds")).toBeVisible();
  await expect(page.getByText("After publishing:")).toBeVisible();
  await expect(page.getByText("3.1% CTR · 41k reach")).toBeVisible();

  await page.getByRole("button", { name: "Bottle design story" }).click();
  await expect(page.getByText("Carousel · Bottle design story")).toBeVisible();
  await expect(page.getByText("Design-led shoppers")).toBeVisible();
  await expect(page.getByText("Jul 21, 2026")).toBeVisible();
  await expect(page.getByText("After publishing:")).toBeHidden();
});

test("the mode toggle switches grid, list, and by-campaign", async ({
  page,
}) => {
  await page.goto("/calendar");

  await page.getByRole("button", { name: "List" }).click();
  await expect(page.getByRole("button", { name: "List" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await expect(page.getByText("True cost of single-use")).toBeVisible();
  await expect(page.getByText("52% open · 6.4% click")).toBeVisible();

  await page.getByRole("button", { name: "By campaign" }).click();
  await expect(page.getByText("3 items").first()).toBeVisible();
  await expect(
    page.getByText("Fernway Refill Launch", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Summer Refill Drop", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Loyalty Newsletter", { exact: true }),
  ).toBeVisible();

  await page.getByRole("button", { name: "Calendar", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Refill in 15 seconds" }),
  ).toBeVisible();
});

import { expect, test } from "@playwright/test";

/**
 * The public half, seen as a visitor with no session.
 *
 * Every test here opens a page the way a person who has just heard of We-OS
 * would — no cookie, no account — and checks what they would see or where they
 * end up. Nothing inspects components or internal state.
 */

test("the root is the Landing, open to a visitor", async ({ page }) => {
  const response = await page.goto("/");

  expect(response?.status()).toBe(200);
  await expect(page).toHaveURL("/");
  await expect(
    page.getByRole("heading", { name: "Strategy before content. Always." }),
  ).toBeVisible();

  const topBar = page.getByRole("banner");
  await expect(topBar.getByRole("link", { name: "Sign in" })).toBeVisible();
  await expect(topBar.getByRole("link", { name: "Get started" })).toBeVisible();

  // The nav rail belongs to the signed-in half; a visitor never sees it.
  await expect(page.locator("aside")).toHaveCount(0);
});

test("Get started and Sign in open the sign-up and sign-in flows", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("banner")
    .getByRole("link", { name: "Get started" })
    .click();
  await expect(page).toHaveURL(/\/sign-up/);
  await expect(page.getByRole("heading", { name: "We-OS" })).toBeVisible();

  await page.goto("/");
  await page.getByRole("banner").getByRole("link", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/sign-in/);
  await expect(page.getByRole("heading", { name: "We-OS" })).toBeVisible();
});

test("Home without a session is sent to sign-in, and remembers where to return", async ({
  page,
}) => {
  await page.goto("/home");

  await expect(page).toHaveURL(/\/sign-in/);
  expect(decodeURIComponent(page.url())).toContain("/home");
});

test("the Landing stacks at a phone width without horizontal scroll", async ({
  page,
}) => {
  await page.setViewportSize({ width: 375, height: 720 });
  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: "Strategy before content. Always." }),
  ).toBeVisible();
  const overflowX = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth,
  );
  expect(overflowX).toBe(false);
});

const TIERS = [
  { name: "Operator", price: "$59", credits: "6,000", param: "operator" },
  { name: "Strategist", price: "$89", credits: "10,000", param: "strategist" },
  { name: "Command", price: "$115", credits: "20,000", param: "command" },
];

test("Pricing shows the three tiers, each linking to sign-up with the tier remembered", async ({
  page,
}) => {
  const response = await page.goto("/pricing");
  expect(response?.status()).toBe(200);

  for (const { name, price, credits, param } of TIERS) {
    const card = page.getByRole("article", { name });
    await expect(card.getByText(price)).toBeVisible();
    await expect(card.getByText(credits)).toBeVisible();
    await expect(
      card.getByRole("link", { name: "Get started" }),
    ).toHaveAttribute("href", `/sign-up?tier=${param}`);
  }

  // Strategist is the default for someone unsure; the other two are not.
  await expect(
    page.getByRole("article", { name: "Strategist" }).getByText("Most chosen"),
  ).toBeVisible();
  await expect(
    page.getByRole("article", { name: "Operator" }).getByText("Most chosen"),
  ).toHaveCount(0);

  await expect(
    page.getByText("Every tier includes the whole product"),
  ).toBeVisible();
});

test("the Landing shows the same three tiers, and Pricing is one link away", async ({
  page,
}) => {
  await page.goto("/");

  const pricing = page.locator("#pricing");
  for (const { name, price, credits, param } of TIERS) {
    const card = pricing.getByRole("article", { name });
    await expect(card.getByText(price)).toBeVisible();
    await expect(card.getByText(credits)).toBeVisible();
    await expect(
      card.getByRole("link", { name: "Get started" }),
    ).toHaveAttribute("href", `/sign-up?tier=${param}`);
  }

  await expect(
    page.getByRole("banner").getByRole("link", { name: "Pricing" }),
  ).toHaveAttribute("href", "/pricing");
  await expect(
    page.getByRole("contentinfo").getByRole("link", { name: "Pricing" }),
  ).toHaveAttribute("href", "/pricing");
});

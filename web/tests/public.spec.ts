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
  await expect(
    page.getByRole("heading", { name: "We-OS", exact: true }),
  ).toBeVisible();

  await page.goto("/");
  await page.getByRole("banner").getByRole("link", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/sign-in/);
  await expect(
    page.getByRole("heading", { name: "We-OS", exact: true }),
  ).toBeVisible();
});

test("Home without a session is sent to sign-in, and remembers where to return", async ({
  page,
}) => {
  await page.goto("/home");

  await expect(page).toHaveURL(/\/sign-in/);
  expect(decodeURIComponent(page.url())).toContain("/home");
});

test("the public pages stack at a phone width without horizontal scroll", async ({
  page,
}) => {
  await page.setViewportSize({ width: 375, height: 720 });

  for (const path of ["/", "/pricing"]) {
    await page.goto(path);
    await expect(page.getByRole("contentinfo")).toBeVisible();
    const overflowX = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth,
    );
    expect(overflowX, `horizontal scroll on ${path}`).toBe(false);
  }
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
    page.getByRole("article", { name: "Strategist" }).getByText("Recommended"),
  ).toBeVisible();
  await expect(
    page.getByRole("article", { name: "Operator" }).getByText("Recommended"),
  ).toHaveCount(0);

  await expect(
    page.getByText("Every tier includes the whole product"),
  ).toBeVisible();
});

test("the tiers live on Pricing, one link away from the Landing", async ({
  page,
}) => {
  await page.goto("/");

  // The Landing tells the story and answers the questions; what it costs is
  // the Pricing page's job, so no tier card appears here.
  await expect(page.getByRole("article")).toHaveCount(0);

  await expect(
    page.getByRole("banner").getByRole("link", { name: "Pricing" }),
  ).toHaveAttribute("href", "/pricing");
  await expect(
    page.getByRole("contentinfo").getByRole("link", { name: "Pricing" }),
  ).toHaveAttribute("href", "/pricing");
});

const FAQ_QUESTIONS = [
  "What is a credit?",
  "Do I need marketing knowledge?",
  "Does We-OS post for me?",
  "Is my data private?",
  "What happens when credits run out?",
];

test("the Landing tells its story in order, from the hero to the final call", async ({
  page,
}) => {
  await page.goto("/");

  await expect(page.getByRole("img", { name: /approval gate/i })).toBeVisible();
  await expect(page.getByRole("heading", { level: 2 })).toHaveText([
    "The work runs. You decide.",
    "Three steps. Your judgement at each one.",
    "Five specialists. One brief. Your sign-off.",
    "Not a content generator.",
    "The ones people ask before paying.",
    "Answer the questions. Approve what runs.",
  ]);
  await expect(page.getByRole("contentinfo")).toBeVisible();
});

test("See how it works reaches the three steps", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "See how it works" }).click();

  await expect(page).toHaveURL(/#how$/);
  await expect(page.locator("#how")).toBeInViewport();
  await expect(
    page.locator("#how").getByRole("heading", { level: 3 }),
  ).toHaveText([
    "Answer what only you know",
    "Research, positioning and planning run in order",
    "Approve each decision as it lands",
  ]);
});

test("the FAQ answers the same five questions on the Landing and on Pricing", async ({
  page,
}) => {
  for (const path of ["/", "/pricing"]) {
    await page.goto(path);
    for (const question of FAQ_QUESTIONS) {
      await expect(
        page.getByText(question),
        `${question} on ${path}`,
      ).toBeVisible();
    }
  }

  // Honest about what does not exist yet: nothing is posted anywhere.
  await page.getByText("Does We-OS post for me?").click();
  await expect(page.getByText("Not yet.")).toBeVisible();
});

test("the copy keeps the voice: no first-person we, no promise the product cannot keep", async ({
  page,
}) => {
  for (const path of ["/", "/pricing"]) {
    await page.goto(path);
    const text = (await page.locator("body").innerText()).replace(/We-OS/g, "");

    expect(text, `first-person "we" on ${path}`).not.toMatch(/\bwe\b/i);
    expect(text, `an unkeepable promise on ${path}`).not.toMatch(
      /free trial|refund|cancel anytime|money.back|testimonial/i,
    );
  }
});

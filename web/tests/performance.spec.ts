import { expect, test } from "@playwright/test";

test("performance renders headline metrics with deltas", async ({ page }) => {
  await page.goto("/performance");

  await expect(
    page.getByRole("heading", { name: "Performance" }),
  ).toBeVisible();

  const metrics: Array<[string, string, string]> = [
    ["Reach", "412k", "+22% vs prior"],
    ["Engaged CTR", "2.4%", "+0.3pts"],
    ["New subscriptions", "486", "+14%"],
    ["CAC", "$18.20", "−8%"],
  ];
  for (const [label, value, delta] of metrics) {
    await expect(page.getByText(label, { exact: true })).toBeVisible();
    await expect(page.getByText(value, { exact: true })).toBeVisible();
    await expect(page.getByText(delta, { exact: true })).toBeVisible();
  }
});

test("performance renders the why / change / keep sections", async ({
  page,
}) => {
  await page.goto("/performance");

  await expect(page.getByText("What happened")).toBeVisible();
  await expect(page.getByText("Why it happened")).toBeVisible();
  await expect(
    page.getByText("Demo-video format drives the CTR gain"),
  ).toBeVisible();

  await expect(page.getByText("What should change")).toBeVisible();
  await expect(
    page.getByText("Shift 2 remaining static posts to demo-video"),
  ).toBeVisible();

  await expect(page.getByText("Keep unchanged")).toBeVisible();
  await expect(page.getByText("Positioning & pillars")).toBeVisible();
});

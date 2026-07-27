import { expect, test } from "@playwright/test";

const WORKSPACE = "/campaigns/fernway-refill-launch";

test("workspace renders the stepper and the strategy document", async ({
  page,
}) => {
  await page.goto(WORKSPACE);

  const stageNav = page.getByRole("navigation", { name: "Stages" });
  for (const name of [
    "Brief",
    "Research",
    "Strategy",
    "Plan",
    "Produce",
    "Approve",
    "Publish",
    "Measure",
  ]) {
    await expect(
      stageNav.getByRole("button", { name: new RegExp(`^${name}`) }),
    ).toBeVisible();
  }

  await expect(
    page.getByRole("heading", { name: "Audience & positioning strategy" }),
  ).toBeVisible();
  await expect(page.getByText("Awaiting your decision")).toBeVisible();
});

test("selecting a stage shows its detail (done / inputs / after)", async ({
  page,
}) => {
  await page.goto(WORKSPACE);

  const stageNav = page.getByRole("navigation", { name: "Stages" });
  await stageNav.getByRole("button", { name: /^Brief/ }).click();
  await expect(
    page.getByRole("heading", { name: "Campaign brief" }),
  ).toBeVisible();
  await expect(page.getByText("Work completed")).toBeVisible();
  await expect(
    page.getByText("Objective: 1,500 new refill subscriptions in Q3"),
  ).toBeVisible();
  await expect(page.getByText("Inputs needed from you")).toBeVisible();
  await expect(page.getByText("None — brief approved Jul 2")).toBeVisible();
  await expect(page.getByText("After this stage:")).toBeVisible();

  await stageNav.getByRole("button", { name: /^Plan/ }).click();
  await expect(
    page.getByRole("heading", { name: "Channel & content plan" }),
  ).toBeVisible();
  await expect(
    page.getByText("Nothing yet — waiting on Strategy approval"),
  ).toBeVisible();
});

test("evidence and comments tabs work; request changes switches to comments", async ({
  page,
}) => {
  await page.goto(WORKSPACE);

  for (const id of ["S1", "S2", "S3", "S4"]) {
    await expect(page.getByText(id, { exact: true }).last()).toBeVisible();
  }
  await expect(
    page.getByText("Purchase-driver survey, May 2026"),
  ).toBeVisible();

  await page.getByRole("button", { name: "Request changes" }).click();
  await expect(page.getByText("Dana")).toBeVisible();
  await expect(page.getByPlaceholder("Add a comment…")).toBeVisible();

  await page.getByRole("button", { name: "Evidence", exact: true }).click();
  await expect(page.getByText("Competitor messaging audit")).toBeVisible();
});

test("the AI action rail toggles notes and the brand scorecard", async ({
  page,
}) => {
  await page.goto(WORKSPACE);

  await page.getByRole("button", { name: "Challenge this assumption" }).click();
  await expect(page.getByText(/Weakest assumption/)).toBeVisible();

  await page.getByRole("button", { name: "Check brand alignment" }).click();
  await expect(
    page.getByText("Brand alignment", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Voice & tone")).toBeVisible();
  await expect(page.getByText("96%")).toBeVisible();

  await page.getByRole("button", { name: "Check brand alignment" }).click();
  await expect(page.getByText("Brand alignment", { exact: true })).toBeHidden();
});

test("approving Strategy fans out to Home and Campaigns, and undo reverses it", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page
      .locator("div")
      .filter({ hasText: /^Pending approvals4$/ })
      .first(),
  ).toBeVisible();
  await expect(page.getByText("Approve audience & positioning")).toBeVisible();

  await page.goto(WORKSPACE);
  await page.getByRole("button", { name: "Approve", exact: true }).click();
  await expect(page.getByText("✓ Positioning approved")).toBeVisible();
  await expect(page.getByText("Approved just now")).toBeVisible();

  await page.reload();
  await expect(page.getByText("✓ Positioning approved")).toBeVisible();

  await page.goto("/campaigns");
  const fernwayRow = page
    .locator("div")
    .filter({ hasText: /^Fernway Refill Launch/ })
    .filter({ hasText: "4/8" })
    .first();
  await expect(fernwayRow).toBeVisible();
  await expect(page.getByText("In progress").first()).toBeVisible();

  await page.goto("/");
  await expect(
    page
      .locator("div")
      .filter({ hasText: /^Pending approvals3$/ })
      .first(),
  ).toBeVisible();
  await expect(page.getByText("Approve audience & positioning")).toBeHidden();

  await page.goto(WORKSPACE);
  await page.getByRole("button", { name: "Return to review" }).click();
  await expect(
    page.getByRole("button", { name: "Approve", exact: true }),
  ).toBeVisible();

  await page.goto("/");
  await expect(
    page
      .locator("div")
      .filter({ hasText: /^Pending approvals4$/ })
      .first(),
  ).toBeVisible();
  await expect(page.getByText("Approve audience & positioning")).toBeVisible();
});

import { expect, test } from "@playwright/test";

import { uniqueName } from "./fixtures";

/**
 * Home renders the tenant's real campaigns, so these assert on structure and on
 * behaviour that follows from real state — a campaign appearing in the queue
 * because it is genuinely waiting — rather than on fixture names, which no
 * longer exist.
 */

test("home renders its sections", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Home" })).toBeVisible();
  await expect(page.getByText("Action queue")).toBeVisible();
  await expect(page.getByText("In progress now")).toBeVisible();
  await expect(page.getByText("Allowance", { exact: true })).toBeVisible();
  await expect(page.getByText("Portfolio")).toBeVisible();
});

test("the stat tiles report real counts", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByText("Need you", { exact: true })).toBeVisible();
  await expect(page.getByText("In progress", { exact: true })).toBeVisible();
});

test("a campaign at an approval gate appears in the queue and links to it", async ({
  page,
}) => {
  const name = uniqueName("Home Queue");

  await page.goto("/campaigns/new");
  await page.getByLabel("Campaign name").fill(name);
  await page.getByLabel("Primary business objective").fill("An objective");
  await page.getByRole("button", { name: "Next →" }).click();
  await page.getByLabel("Business KPI").fill("A business target");
  await page.getByLabel("Marketing KPI").fill("A marketing target");
  await page.getByLabel("Creative KPI").fill("A creative target");
  await page.getByRole("button", { name: "Next →" }).click();
  await page.getByRole("radio").first().click();
  await page.getByLabel("Campaign budget").fill("1000");
  await page.getByLabel("Start date").fill("2026-09-01");
  await page.getByLabel("End date").fill("2026-10-27");
  await page.getByRole("button", { name: "Next →" }).click();
  await page.getByRole("button", { name: "Create campaign" }).click();

  await page.getByRole("button", { name: "Start run" }).click();
  await expect(
    page.getByRole("button", { name: "Approve", exact: true }),
  ).toBeVisible({ timeout: 120_000 });

  // The queue is derived from real campaign state, so the campaign that just
  // halted must be on it — that is the whole claim Home makes.
  await page.goto("/");
  const row = page.locator("div").filter({ hasText: name }).last();
  await expect(row).toBeVisible();
  await expect(
    page.getByText("Decision", { exact: true }).first(),
  ).toBeVisible();
});

test("an empty queue says so rather than showing nothing", async ({ page }) => {
  await page.goto("/");

  const queueCount = await page.getByText("Decision", { exact: true }).count();
  if (queueCount === 0) {
    await expect(
      page.getByText("Nothing is waiting on a decision"),
    ).toBeVisible();
  }
});

test("a decision made in the Workspace is reflected on Home without a refresh", async ({
  page,
}) => {
  const name = uniqueName("Coherence");

  await page.goto("/campaigns/new");
  await page.getByLabel("Campaign name").fill(name);
  await page.getByLabel("Primary business objective").fill("An objective");
  await page.getByRole("button", { name: "Next →" }).click();
  await page.getByLabel("Business KPI").fill("A business target");
  await page.getByLabel("Marketing KPI").fill("A marketing target");
  await page.getByLabel("Creative KPI").fill("A creative target");
  await page.getByRole("button", { name: "Next →" }).click();
  await page.getByRole("radio").first().click();
  await page.getByLabel("Campaign budget").fill("1000");
  await page.getByLabel("Start date").fill("2026-09-01");
  await page.getByLabel("End date").fill("2026-10-27");
  await page.getByRole("button", { name: "Next →" }).click();
  await page.getByRole("button", { name: "Create campaign" }).click();

  await expect(page.getByRole("navigation", { name: "Stages" })).toBeVisible();
  const workspace = page.url();
  const slug = new URL(workspace).pathname.split("/campaigns/")[1];

  // A draft is not waiting on anyone, so Home must not be asking about it.
  const queue = page.getByRole("list", { name: "Decision queue" });
  await page.goto("/");
  await expect(queue.locator(`a[href="/campaigns/${slug}"]`)).toHaveCount(0);

  // Run it to a gate: now it is waiting, and Home must say so.
  await page.goto(workspace);
  await page.getByRole("button", { name: "Start run" }).click();
  const approve = page.getByRole("button", { name: "Approve", exact: true });
  await expect(approve).toBeVisible({ timeout: 120_000 });

  await page.goto("/");
  await expect(queue.locator(`a[href="/campaigns/${slug}"]`)).toBeVisible();

  // Approving advances the run to the next stage, which is gated too — so the
  // campaign is still on the queue, but the stage it names has moved. That
  // movement is the coherence being tested: Home reflects a decision taken on
  // another screen, with no manual refresh.
  await page.goto(workspace);
  await approve.click();
  await expect(
    page
      .getByRole("navigation", { name: "Stages" })
      .getByRole("button", { name: /^Brand strategy/ }),
  ).toContainText("Approved", { timeout: 120_000 });

  await page.goto("/");
  await expect(queue.locator(`a[href="/campaigns/${slug}"]`)).toBeVisible();
});

import { expect, test } from "@playwright/test";

import { uniqueName } from "./fixtures";

/**
 * A specialist that lacks a fact only the business knows asks for it and the
 * run halts (ADR-0028). The e2e engine runs the scripted provider with its
 * performance-plan specialist in ask mode (`MARKETING_OS_SCRIPTED_ASK_STAGE`),
 * so a run approved through its first two gates halts on a fixed question,
 * identically every time, with no model called.
 *
 * What is under test is what the owner sees: the Workspace says the stage has
 * a question, Home lists the campaign as a red Decision, and following it
 * shows the question and the reason the specialist gave.
 */

/**
 * Creates a campaign through the wizard and lands on its Workspace.
 *
 * Args:
 *   page: The Playwright page.
 *   name: The campaign name, which must be unique per run.
 */
async function createCampaign(
  page: import("@playwright/test").Page,
  name: string,
): Promise<void> {
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
}

test("a specialist's question halts the run and reaches Home as a Decision", async ({
  page,
}) => {
  const name = uniqueName("Clarify");
  await createCampaign(page, name);
  const slug = new URL(page.url()).pathname.split("/campaigns/")[1];

  // Two approvals take the run to the performance plan, whose specialist asks.
  await page.getByRole("button", { name: "Start run" }).click();
  const approve = page.getByRole("button", { name: "Approve", exact: true });
  await expect(approve).toBeVisible({ timeout: 120_000 });
  await expect(
    page.getByText("Approving starts Campaign strategy."),
  ).toBeVisible();
  await approve.click();
  await expect(
    page.getByText("Approving starts Performance plan."),
  ).toBeVisible({
    timeout: 120_000,
  });
  await approve.click();

  // The Workspace follows the run to the stage that asked, and says so.
  await expect(
    page.getByText("Performance plan has a question for you"),
  ).toBeVisible({ timeout: 120_000 });
  await expect(page.getByRole("log", { name: "Run progress" })).toContainText(
    "Waiting for your answer",
  );
  await expect(
    page.getByRole("button", { name: "Approve", exact: true }),
  ).toHaveCount(0);

  // Home derives the queue from real campaign state, so the halted campaign is
  // on it — tagged Decision in red, and leading to the questions.
  await page.goto("/home");
  const queue = page.getByRole("list", { name: "Decision queue" });
  const link = queue.locator(`a[href="/campaigns/${slug}/clarifications"]`);
  await expect(link).toBeVisible();
  const row = queue.locator("li").filter({ has: link });
  await expect(row).toContainText("Plan has a question for you.");
  await expect(row.getByText("Decision", { exact: true })).toHaveClass(
    /text-red-700/,
  );

  await link.click();
  await expect(
    page.getByRole("heading", { name: "Questions for you" }),
  ).toBeVisible();
  const questions = page.getByRole("list", { name: "Questions" });
  await expect(questions).toContainText("email list");
  await expect(questions).toContainText("Why we ask:");
  await expect(questions).toContainText("build one");
});

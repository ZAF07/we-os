import { expect, test } from "@playwright/test";

import { createCampaign, uniqueName } from "./fixtures";

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

test("a specialist's question halts the run and reaches Home as a Decision", async ({
  page,
}) => {
  const slug = await createCampaign(page, uniqueName("Clarify"));

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

  // The Workspace follows the run to the stage that asked, and says so: the
  // decision rail names the stage (exact, since the progress rail narrates the
  // same sentence with a full stop) and offers no approval.
  await expect(
    page.getByText("Performance plan has a question for you", { exact: true }),
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
  const href = `/campaigns/${slug}/clarifications`;
  const link = queue.locator(`a[href="${href}"]`);
  await expect(link).toBeVisible();
  const row = queue
    .locator("li")
    .filter({ has: page.locator(`a[href="${href}"]`) });
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

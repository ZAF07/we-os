import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ClarificationsForm } from "@/components/workspace/clarifications-form";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, refresh: vi.fn() }),
}));

afterEach(() => {
  cleanup();
  push.mockReset();
});

const pending = {
  run_id: "run_1",
  slug: "summer-push",
  stage: "performance-plan",
  questions: [
    {
      question: "Does the business have an email list?",
      reason: "Email needs a list.",
    },
    { question: "How big is it?", reason: "Size decides the channel's role." },
  ],
};

describe("ClarificationsForm", () => {
  it("offers one answer box per question, labelled by the question, and waits for all of them", () => {
    render(
      <ClarificationsForm
        slug="summer-push"
        pending={pending}
        submit={vi.fn()}
      />,
    );

    const first = screen.getByLabelText(
      "Does the business have an email list?",
    );
    const second = screen.getByLabelText("How big is it?");
    const send = screen.getByRole("button", { name: "Send answers" });
    expect(screen.getByText("Why we ask: Email needs a list.")).toBeDefined();
    expect(send.hasAttribute("disabled")).toBe(true);

    fireEvent.change(first, { target: { value: "Yes" } });
    expect(send.hasAttribute("disabled")).toBe(true);
    fireEvent.change(second, { target: { value: "About 1,200" } });
    expect(send.hasAttribute("disabled")).toBe(false);
  });

  it("sends every answer paired with its question, then moves to the Workspace", async () => {
    const submit = vi.fn().mockResolvedValue({ error: null });
    render(
      <ClarificationsForm
        slug="summer-push"
        pending={pending}
        submit={submit}
      />,
    );
    fireEvent.change(
      screen.getByLabelText("Does the business have an email list?"),
      { target: { value: "  Yes  " } },
    );
    fireEvent.change(screen.getByLabelText("How big is it?"), {
      target: { value: "About 1,200" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Send answers" }));

    await waitFor(() =>
      expect(push).toHaveBeenCalledWith("/campaigns/summer-push"),
    );
    expect(submit).toHaveBeenCalledWith("summer-push", "run_1", [
      { question: "Does the business have an email list?", answer: "Yes" },
      { question: "How big is it?", answer: "About 1,200" },
    ]);
  });

  it("shows the engine's refusal and stays on the page", async () => {
    const submit = vi.fn().mockResolvedValue({
      error: "Run 'run_1' is not waiting for a clarification.",
    });
    render(
      <ClarificationsForm
        slug="summer-push"
        pending={pending}
        submit={submit}
      />,
    );
    fireEvent.change(
      screen.getByLabelText("Does the business have an email list?"),
      { target: { value: "Yes" } },
    );
    fireEvent.change(screen.getByLabelText("How big is it?"), {
      target: { value: "About 1,200" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Send answers" }));

    await waitFor(() =>
      expect(screen.getByRole("alert").textContent).toContain("not waiting"),
    );
    expect(push).not.toHaveBeenCalled();
  });
});

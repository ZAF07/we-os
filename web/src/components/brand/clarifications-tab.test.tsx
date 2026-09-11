import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ClarificationsTab } from "@/components/brand/clarifications-tab";

const refresh = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh }),
}));

afterEach(() => {
  cleanup();
  refresh.mockReset();
});

const emailList = {
  id: "clr_1",
  question: "Does the business have an email list?",
  reason: "Email needs a list.",
  answer: "Yes, about 1,200 subscribers.",
  stage: "performance-plan",
  slug: "summer-push",
  answered_at: "2026-09-11T09:00:00Z",
};

describe("ClarificationsTab", () => {
  it("lists each Clarification with its question, reason, origin and answer", () => {
    render(<ClarificationsTab clarifications={[emailList]} save={vi.fn()} />);

    const list = screen.getByRole("list", { name: "Clarifications" });
    expect(list.textContent).toContain("Does the business have an email list?");
    expect(list.textContent).toContain("Why it was asked: Email needs a list.");
    expect(list.textContent).toContain(
      "Asked by Performance plan for campaign summer-push",
    );
    expect(list.textContent).toContain("Yes, about 1,200 subscribers.");
  });

  it("explains where Clarifications come from when there are none", () => {
    render(<ClarificationsTab clarifications={[]} save={vi.fn()} />);

    expect(screen.queryByRole("list", { name: "Clarifications" })).toBeNull();
    expect(screen.getByText(/No Clarifications yet/).textContent).toContain(
      "asks you during a campaign",
    );
  });

  it("saves an edited answer in place and shows the saved text", async () => {
    const save = vi
      .fn()
      .mockResolvedValue({ ...emailList, answer: "No list yet." });
    render(<ClarificationsTab clarifications={[emailList]} save={save} />);

    fireEvent.click(
      screen.getByRole("button", {
        name: "Edit answer: Does the business have an email list?",
      }),
    );
    fireEvent.change(
      screen.getByLabelText("Does the business have an email list?"),
      { target: { value: "  No list yet.  " } },
    );
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(refresh).toHaveBeenCalled());
    expect(save).toHaveBeenCalledWith("clr_1", "No list yet.");
    expect(screen.getByText("No list yet.")).toBeDefined();
    expect(screen.queryByText("Yes, about 1,200 subscribers.")).toBeNull();
    expect(screen.queryByRole("button", { name: "Save" })).toBeNull();
  });

  it("refuses a blank answer rather than saving it", () => {
    const save = vi.fn();
    render(<ClarificationsTab clarifications={[emailList]} save={save} />);

    fireEvent.click(
      screen.getByRole("button", {
        name: "Edit answer: Does the business have an email list?",
      }),
    );
    fireEvent.change(
      screen.getByLabelText("Does the business have an email list?"),
      { target: { value: "   " } },
    );
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(screen.getByRole("alert").textContent).toContain(
      "An answer cannot be blank.",
    );
    expect(save).not.toHaveBeenCalled();
  });

  it("shows a failed save and keeps the edit open", async () => {
    const save = vi.fn().mockRejectedValue(new Error("engine down"));
    render(<ClarificationsTab clarifications={[emailList]} save={save} />);

    fireEvent.click(
      screen.getByRole("button", {
        name: "Edit answer: Does the business have an email list?",
      }),
    );
    fireEvent.change(
      screen.getByLabelText("Does the business have an email list?"),
      { target: { value: "No list yet." } },
    );
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(screen.getByRole("alert").textContent).toContain(
        "Could not save that answer.",
      ),
    );
    expect(screen.getByRole("button", { name: "Save" })).toBeDefined();
    expect(refresh).not.toHaveBeenCalled();
  });
});

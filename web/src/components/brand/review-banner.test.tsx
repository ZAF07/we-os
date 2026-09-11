import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ReviewBanner } from "@/components/brand/review-banner";

const refresh = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh }),
}));

afterEach(() => {
  cleanup();
  refresh.mockReset();
});

const due = { due: true, reviewed_at: "2026-09-03T09:00:00Z" };

describe("ReviewBanner", () => {
  it("shows nothing when no review is due", () => {
    render(
      <ReviewBanner
        review={{ due: false, reviewed_at: "2026-09-10T09:00:00Z" }}
        markReviewed={vi.fn()}
      />,
    );

    expect(
      screen.queryByRole("region", { name: "Brand DNA review" }),
    ).toBeNull();
  });

  it("shows nothing when the review could not be read", () => {
    render(<ReviewBanner review={null} markReviewed={vi.fn()} />);

    expect(
      screen.queryByRole("region", { name: "Brand DNA review" }),
    ).toBeNull();
  });

  it("asks for a look and offers Reviewed when one is due", () => {
    render(<ReviewBanner review={due} markReviewed={vi.fn()} />);

    const banner = screen.getByRole("region", { name: "Brand DNA review" });
    expect(banner.textContent).toContain("Time to look over your Brand DNA");
    expect(screen.getByRole("button", { name: "Reviewed" })).toBeTruthy();
  });

  it("records the review, hides itself, and refreshes the page", async () => {
    const markReviewed = vi
      .fn()
      .mockResolvedValue({ due: false, reviewed_at: "2026-09-11T09:00:00Z" });
    render(<ReviewBanner review={due} markReviewed={markReviewed} />);

    fireEvent.click(screen.getByRole("button", { name: "Reviewed" }));

    await waitFor(() =>
      expect(
        screen.queryByRole("region", { name: "Brand DNA review" }),
      ).toBeNull(),
    );
    expect(markReviewed).toHaveBeenCalledTimes(1);
    expect(refresh).toHaveBeenCalledTimes(1);
  });

  it("stays, and says so, when the review could not be recorded", async () => {
    const markReviewed = vi.fn().mockRejectedValue(new Error("engine down"));
    render(<ReviewBanner review={due} markReviewed={markReviewed} />);

    fireEvent.click(screen.getByRole("button", { name: "Reviewed" }));

    await waitFor(() =>
      expect(screen.getByRole("alert").textContent).toContain(
        "Could not mark it reviewed",
      ),
    );
    expect(screen.getByRole("button", { name: "Reviewed" })).toBeTruthy();
    expect(refresh).not.toHaveBeenCalled();
  });

  it("shows the next review that falls due after one was dismissed", async () => {
    const markReviewed = vi
      .fn()
      .mockResolvedValue({ due: false, reviewed_at: "2026-09-11T09:00:00Z" });
    const { rerender } = render(
      <ReviewBanner review={due} markReviewed={markReviewed} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Reviewed" }));
    await waitFor(() =>
      expect(
        screen.queryByRole("region", { name: "Brand DNA review" }),
      ).toBeNull(),
    );

    rerender(
      <ReviewBanner
        review={{ due: true, reviewed_at: "2026-09-11T09:00:00Z" }}
        markReviewed={markReviewed}
      />,
    );

    expect(
      screen.getByRole("region", { name: "Brand DNA review" }),
    ).toBeTruthy();
  });
});

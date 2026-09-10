import { act } from "react";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { Campaign } from "@/lib/engine";

const loadStage = vi.fn();

/**
 * Whether Clerk's browser script has loaded, as the Workspace sees it — the
 * state the session-readiness hook answers from. Read on every render, so a
 * test flips it and re-renders to play the script finishing after mount.
 */
let clerkLoaded = true;

/** How many times the Workspace has rendered, counted at the hook it calls once per render. */
let renders = 0;

vi.mock("@clerk/nextjs", () => ({
  useClerk: () => {
    renders += 1;
    return { loaded: clerkLoaded };
  },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
  }: {
    href: string;
    children: React.ReactNode;
  }) => <a href={href}>{children}</a>,
}));

vi.mock("@/app/(app)/campaigns/[slug]/actions", () => ({
  loadStage: async (slug: string, stageKey: string) =>
    loadStage(slug, stageKey),
  loadVersion: vi.fn(),
  approveStageAction: vi.fn(),
  reopenStageAction: vi.fn(),
  reviseStageAction: vi.fn(),
  startRunAction: vi.fn(),
}));

const { Workspace } = await import("@/components/workspace/workspace");

const PENDING = {
  state: "pending",
  approval_policy: "human",
  latest_version: null,
  stale: false,
};

const CAMPAIGN: Campaign = {
  id: "spring-push",
  name: "Spring push",
  objective: "120 refill subscriptions",
  timeframe: { start_date: "2026-09-01", end_date: "2026-10-27" },
  budget: { amount: 4000, currency: "SGD" },
  audience_segment: "Urban beginners",
  kpis: {
    business: "120 subscriptions",
    marketing: "2.5% conversion",
    creative: "30% hook rate",
  },
  status: "draft",
  stages: [
    { key: "research", phase: "Research", ...PENDING },
    { key: "brand-strategy", phase: "Strategy", ...PENDING },
  ],
};

const EMPTY_VIEW = { deliverable: null, versions: [] };

afterEach(cleanup);
beforeEach(() => {
  loadStage.mockReset();
  clerkLoaded = true;
  renders = 0;
});

describe("the Workspace's first load", () => {
  it("waits for the session to be ready, then loads the stage once", async () => {
    clerkLoaded = false;
    loadStage.mockResolvedValue(EMPTY_VIEW);
    const { rerender } = render(<Workspace campaign={CAMPAIGN} runId={null} />);
    await act(async () => {});

    // The page is up, but the script has not refreshed the token yet: a server
    // action fired now would be refused as expired.
    expect(loadStage).not.toHaveBeenCalled();

    clerkLoaded = true;
    rerender(<Workspace campaign={CAMPAIGN} runId={null} />);
    await waitFor(() => expect(loadStage).toHaveBeenCalledTimes(1));
    expect(loadStage).toHaveBeenCalledWith("spring-push", "research");

    // Readiness is a one-way door: later renders do not ask again.
    rerender(<Workspace campaign={CAMPAIGN} runId={null} />);
    await act(async () => {});
    expect(loadStage).toHaveBeenCalledTimes(1);
  });

  it("loads the stage in its first render when the session is already ready", async () => {
    let rendersBeforeTheLoad = 0;
    loadStage.mockImplementation(async () => {
      rendersBeforeTheLoad = renders;
      return EMPTY_VIEW;
    });
    render(<Workspace campaign={CAMPAIGN} runId={null} />);
    await waitFor(() => expect(loadStage).toHaveBeenCalledTimes(1));

    // No render was spent waiting: a page whose script has loaded — every
    // client-side navigation — loads exactly as it did before the wait existed.
    expect(rendersBeforeTheLoad).toBe(1);
    expect(await screen.findByText(/Nothing produced yet/)).toBeDefined();
  });

  it("says the stage could not be loaded when the load itself fails", async () => {
    loadStage.mockRejectedValue(new Error("engine unreachable"));
    render(<Workspace campaign={CAMPAIGN} runId={null} />);

    expect(await screen.findByRole("alert")).toHaveProperty(
      "textContent",
      "Could not load this stage. Try again.",
    );
  });
});

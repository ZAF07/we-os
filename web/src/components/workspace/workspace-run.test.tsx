import { act } from "react";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { Campaign, CampaignStage } from "@/lib/engine";

const loadStage = vi.fn();
const approveStageAction = vi.fn();
const startRunAction = vi.fn();

vi.mock("@clerk/nextjs", () => ({
  useClerk: () => ({ loaded: true }),
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
  approveStageAction: async (slug: string, runId: string, stageKey: string) =>
    approveStageAction(slug, runId, stageKey),
  reopenStageAction: vi.fn(),
  reviseStageAction: vi.fn(),
  startRunAction: async (slug: string, stageKey: string | null) =>
    startRunAction(slug, stageKey),
}));

const { Workspace } = await import("@/components/workspace/workspace");

/**
 * A stand-in for the browser's EventSource, so a test can play the engine's
 * run stream event by event and assert what the Workspace makes of each one.
 */
class FakeEventSource {
  static opened: FakeEventSource[] = [];
  onmessage: ((message: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  closed = false;

  constructor(public readonly url: string) {
    FakeEventSource.opened.push(this);
  }

  close(): void {
    this.closed = true;
  }
}

/**
 * Plays one trace event through the newest open stream.
 *
 * Args:
 *   event: The event as the engine would emit it.
 */
async function emit(event: Record<string, unknown>): Promise<void> {
  const source = FakeEventSource.opened.at(-1);
  if (!source) throw new Error("no stream is open");
  await act(async () => {
    source.onmessage?.({ data: JSON.stringify(event) });
  });
}

/**
 * Builds a stage as the engine reports one.
 *
 * Args:
 *   key: The engine stage key.
 *   phase: The operator Phase the stage belongs to.
 *   overrides: The fields this stage differs from a pending stage in.
 *
 * Returns:
 *   The stage.
 */
function stage(
  key: string,
  phase: string,
  overrides: Partial<CampaignStage> = {},
): CampaignStage {
  return {
    key,
    phase,
    state: "pending",
    approval_policy: "human",
    latest_version: null,
    stale: false,
    ...overrides,
  };
}

/**
 * Builds a campaign as the engine reports one.
 *
 * Args:
 *   stages: The campaign's stages in pipeline order.
 *   status: The campaign's lifecycle status.
 *
 * Returns:
 *   The campaign.
 */
function campaign(stages: CampaignStage[], status = "running"): Campaign {
  return {
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
    status,
    stages,
  };
}

const FRESH = campaign([
  stage("research", "Research"),
  stage("brand-strategy", "Strategy"),
  stage("campaign-strategy", "Strategy"),
  stage("performance-plan", "Plan"),
]);

const AT_BRAND_GATE = campaign(
  [
    stage("research", "Research", { state: "completed", latest_version: 1 }),
    stage("brand-strategy", "Strategy", {
      state: "awaiting_approval",
      latest_version: 1,
    }),
    stage("campaign-strategy", "Strategy"),
    stage("performance-plan", "Plan"),
  ],
  "awaiting_approval",
);

const EMPTY_VIEW = { deliverable: null, versions: [] };

/**
 * Finds a stage's entry in the Stages list.
 *
 * Args:
 *   title: The stage's title as the interface names it.
 *
 * Returns:
 *   The list entry.
 */
function stageEntry(title: string): HTMLElement {
  const nav = screen.getByRole("navigation", { name: "Stages" });
  return within(nav).getByRole("button", { name: new RegExp(`^${title}`) });
}

afterEach(cleanup);
beforeEach(() => {
  loadStage.mockReset();
  loadStage.mockResolvedValue(EMPTY_VIEW);
  approveStageAction.mockReset();
  startRunAction.mockReset();
  FakeEventSource.opened = [];
  vi.stubGlobal("EventSource", FakeEventSource);
});

describe("the stage a run is working on", () => {
  it("is marked in the Stages list once the stream says it started", async () => {
    render(<Workspace campaign={FRESH} runId="run-1" />);
    await waitFor(() => expect(FakeEventSource.opened).toHaveLength(1));

    await emit({ event: "gate.passed" });
    await emit({ event: "stage.start", stage: "research" });

    expect(stageEntry("Research findings").textContent).toContain(
      "In progress",
    );
    expect(stageEntry("Research findings").textContent).not.toContain(
      "Not started",
    );
    expect(stageEntry("Brand strategy").textContent).toContain("Not started");

    // The phase chip holding the running stage pulses; the others do not.
    expect(
      screen.getByRole("button", { name: /^1\s?Research$/ }).innerHTML,
    ).toContain("animate-pulse");
    expect(
      screen.getByRole("button", { name: /^2\s?Strategy$/ }).innerHTML,
    ).not.toContain("animate-pulse");
  });

  it("is read correctly by a page reloaded after an approval", async () => {
    render(<Workspace campaign={AT_BRAND_GATE} runId="run-1" />);
    await waitFor(() => expect(FakeEventSource.opened).toHaveLength(1));

    // The stream replays the whole trace: the first segment, the gate the run
    // halted at, then what it did once approved.
    await emit({ event: "stage.start", stage: "research" });
    await emit({ event: "stage.done", stage: "research" });
    await emit({ event: "stage.start", stage: "brand-strategy" });
    await emit({ event: "stage.done", stage: "brand-strategy" });
    await emit({ event: "run.summary", outcome: "awaiting_approval" });
    await emit({ event: "stage.approved", stage: "brand-strategy" });
    await emit({ event: "stage.start", stage: "campaign-strategy" });

    expect(stageEntry("Campaign strategy").textContent).toContain(
      "In progress",
    );
    expect(stageEntry("Brand strategy").textContent).not.toContain(
      "In progress",
    );
    const log = screen.getByRole("log", { name: "Run progress" });
    expect(log.textContent).toContain("Working");
    expect(log.textContent).toContain("You approved Brand strategy.");
  });

  it("moves with the run and clears when the run ends", async () => {
    render(<Workspace campaign={FRESH} runId="run-1" />);
    await waitFor(() => expect(FakeEventSource.opened).toHaveLength(1));

    await emit({ event: "stage.start", stage: "research" });
    await emit({ event: "stage.done", stage: "research" });
    await emit({ event: "stage.start", stage: "brand-strategy" });

    expect(stageEntry("Brand strategy").textContent).toContain("In progress");
    expect(stageEntry("Research findings").textContent).not.toContain(
      "In progress",
    );

    await emit({ event: "run.summary", outcome: "ok" });
    expect(stageEntry("Brand strategy").textContent).not.toContain(
      "In progress",
    );
  });

  it("is still marked when a person is reading a different stage", async () => {
    render(<Workspace campaign={FRESH} runId="run-1" />);
    await waitFor(() => expect(FakeEventSource.opened).toHaveLength(1));
    await emit({ event: "stage.start", stage: "research" });

    fireEvent.click(stageEntry("Performance plan"));

    // Selection and running are separate marks: the person reads one stage
    // while the system works on another, and the list says both.
    expect(stageEntry("Performance plan").getAttribute("aria-current")).toBe(
      "step",
    );
    expect(stageEntry("Performance plan").textContent).toContain("Not started");
    expect(
      stageEntry("Research findings").getAttribute("aria-current"),
    ).toBeNull();
    expect(stageEntry("Research findings").textContent).toContain(
      "In progress",
    );
  });
});

describe("the document pane of the stage a run is working on", () => {
  /**
   * Finds the document pane by the stage heading it shows.
   *
   * Args:
   *   title: The stage's title as the interface names it.
   *
   * Returns:
   *   The pane holding the status pill, the heading, and the deliverable.
   */
  function pane(title: string): HTMLElement {
    const heading = screen.getByRole("heading", { level: 2, name: title });
    return heading.parentElement as HTMLElement;
  }

  it("says the stage is running, not that it waits on approvals", async () => {
    render(<Workspace campaign={FRESH} runId="run-1" />);
    await waitFor(() => expect(FakeEventSource.opened).toHaveLength(1));
    await emit({ event: "stage.start", stage: "research" });
    await screen.findByText(/Nothing produced yet|running now/);

    // Everything before this stage is approved — that is why the run is on
    // it. The pane must not claim otherwise.
    const document = pane("Research findings");
    expect(document.textContent).toContain("This stage is running now");
    expect(document.textContent).not.toContain("Nothing produced yet");
    expect(document.textContent).toContain("In progress");
    expect(document.textContent).not.toContain("Not started");
  });

  it("keeps the approval precondition for a stage the run has not reached", async () => {
    render(<Workspace campaign={FRESH} runId="run-1" />);
    await waitFor(() => expect(FakeEventSource.opened).toHaveLength(1));
    await emit({ event: "stage.start", stage: "research" });

    fireEvent.click(stageEntry("Brand strategy"));
    await screen.findByText(/Nothing produced yet/);

    const document = pane("Brand strategy");
    expect(document.textContent).toContain("Nothing produced yet");
    expect(document.textContent).not.toContain("running now");
    expect(document.textContent).toContain("Not started");
  });

  it("stops saying the stage is running once the run has left it", async () => {
    render(<Workspace campaign={FRESH} runId="run-1" />);
    await waitFor(() => expect(FakeEventSource.opened).toHaveLength(1));
    await emit({ event: "stage.start", stage: "research" });
    await screen.findByText(/running now/);

    await emit({ event: "stage.failed", stage: "research" });

    const document = pane("Research findings");
    expect(document.textContent).not.toContain("running now");
    expect(document.textContent).toContain("Not started");
  });
});

describe("approving a stage", () => {
  it("names the stage the approval will start, before the click", async () => {
    render(<Workspace campaign={AT_BRAND_GATE} runId="run-1" />);

    expect(
      await screen.findByText(/Approving starts Campaign strategy/),
    ).toBeDefined();
  });

  it("keeps the progress feed on screen and marks the next stage as started", async () => {
    approveStageAction.mockResolvedValue({ error: null });
    render(<Workspace campaign={AT_BRAND_GATE} runId="run-1" />);
    await waitFor(() => expect(FakeEventSource.opened).toHaveLength(1));
    await emit({ event: "stage.start", stage: "research" });
    await emit({ event: "stage.done", stage: "research" });
    await emit({ event: "run.summary", outcome: "awaiting_approval" });

    fireEvent.click(screen.getByRole("button", { name: "Approve" }));
    await waitFor(() => expect(approveStageAction).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(FakeEventSource.opened).toHaveLength(2));

    // The stream is re-attaching and has replayed nothing yet. The feed the
    // person was reading a moment ago is still there, headed Working, and
    // the Stages list already says which stage the approval set going.
    const log = screen.getByRole("log", { name: "Run progress" });
    expect(log.textContent).toContain("Working");
    expect(log.textContent).toContain("Finished Research findings.");
    expect(stageEntry("Campaign strategy").textContent).toContain(
      "In progress",
    );

    // The replay repeats what the page already saw, gate summary included.
    // None of it is news: the list keeps saying what the approval started, and
    // the replayed gate is not mistaken for the run halting again.
    await emit({ event: "stage.start", stage: "research" });
    await emit({ event: "stage.done", stage: "research" });
    await emit({ event: "run.summary", outcome: "awaiting_approval" });
    expect(log.textContent).toContain("Working");
    expect(log.textContent).not.toContain("Waiting for your decision");
    expect(stageEntry("Campaign strategy").textContent).toContain(
      "In progress",
    );

    // Past the replay, the stream is the source of truth again.
    await emit({ event: "stage.approved", stage: "brand-strategy" });
    expect(log.textContent).toContain("You approved Brand strategy.");
    await emit({ event: "stage.start", stage: "campaign-strategy" });
    expect(stageEntry("Campaign strategy").textContent).toContain(
      "In progress",
    );
  });

  it("says the feed was lost, not that the run is waiting, if re-attaching fails", async () => {
    approveStageAction.mockResolvedValue({ error: null });
    render(<Workspace campaign={AT_BRAND_GATE} runId="run-1" />);
    await waitFor(() => expect(FakeEventSource.opened).toHaveLength(1));
    await emit({ event: "stage.start", stage: "research" });
    await emit({ event: "run.summary", outcome: "awaiting_approval" });
    expect(
      screen.getByRole("log", { name: "Run progress" }).textContent,
    ).toContain("Waiting for your decision");

    fireEvent.click(screen.getByRole("button", { name: "Approve" }));
    await waitFor(() => expect(FakeEventSource.opened).toHaveLength(2));
    await act(async () => {
      FakeEventSource.opened[1].onerror?.();
    });

    expect(screen.getByRole("alert").textContent).toContain(
      "Lost the live feed",
    );
    expect(screen.queryByText("Waiting for your decision")).toBeNull();
  });

  it("marks the stage a re-run sets going, not the one a past approval did", async () => {
    approveStageAction.mockResolvedValue({ error: null });
    startRunAction.mockResolvedValue({ error: null });
    const { rerender } = render(
      <Workspace campaign={AT_BRAND_GATE} runId="run-1" />,
    );
    await waitFor(() => expect(FakeEventSource.opened).toHaveLength(1));

    fireEvent.click(screen.getByRole("button", { name: "Approve" }));
    await waitFor(() => expect(FakeEventSource.opened).toHaveLength(2));
    expect(stageEntry("Campaign strategy").textContent).toContain(
      "In progress",
    );

    // Later, a stale Research is re-run from its banner. What is starting now
    // is Research, whatever the last approval started.
    const stale = campaign(
      [
        stage("research", "Research", {
          state: "stale",
          stale: true,
          latest_version: 1,
        }),
        stage("brand-strategy", "Strategy", {
          state: "completed",
          latest_version: 1,
        }),
        stage("campaign-strategy", "Strategy"),
        stage("performance-plan", "Plan"),
      ],
      "running",
    );
    loadStage.mockResolvedValue({
      deliverable: { name: "research.md", path: "x", content: "# R" },
      versions: [],
    });
    rerender(<Workspace campaign={stale} runId="run-1" />);
    fireEvent.click(stageEntry("Research findings"));
    fireEvent.click(await screen.findByRole("button", { name: /Re-run/ }));
    await waitFor(() => expect(startRunAction).toHaveBeenCalledTimes(1));

    expect(stageEntry("Research findings").textContent).toContain(
      "In progress",
    );
    expect(stageEntry("Campaign strategy").textContent).toContain(
      "Not started",
    );
  });

  it("follows the run to the next gate even after a person browsed elsewhere", async () => {
    approveStageAction.mockResolvedValue({ error: null });
    const { rerender } = render(
      <Workspace campaign={AT_BRAND_GATE} runId="run-1" />,
    );

    fireEvent.click(stageEntry("Research findings"));
    expect(stageEntry("Research findings").getAttribute("aria-current")).toBe(
      "step",
    );

    fireEvent.click(stageEntry("Brand strategy"));
    fireEvent.click(screen.getByRole("button", { name: "Approve" }));
    await waitFor(() => expect(approveStageAction).toHaveBeenCalledTimes(1));

    const atNextGate = campaign(
      [
        stage("research", "Research", {
          state: "completed",
          latest_version: 1,
        }),
        stage("brand-strategy", "Strategy", {
          state: "completed",
          latest_version: 1,
        }),
        stage("campaign-strategy", "Strategy", {
          state: "awaiting_approval",
          latest_version: 1,
        }),
        stage("performance-plan", "Plan"),
      ],
      "awaiting_approval",
    );
    rerender(<Workspace campaign={atNextGate} runId="run-1" />);

    expect(stageEntry("Campaign strategy").getAttribute("aria-current")).toBe(
      "step",
    );
    expect(
      screen.getByRole("heading", { level: 2, name: "Campaign strategy" }),
    ).toBeDefined();
  });
});

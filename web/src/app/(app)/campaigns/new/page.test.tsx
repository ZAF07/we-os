import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { AudienceSegment } from "@/lib/engine";

const loadAudienceSegments = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("../actions", () => ({
  loadAudienceSegments: async () => loadAudienceSegments(),
  createCampaignAction: vi.fn(),
}));

/**
 * A failing load, shaped the way the real action fails.
 *
 * Rejects from inside the call so the page owns the rejection for the whole of
 * its life, rather than it existing before the page has a handler attached.
 */
function failsWith(message: string) {
  return async () => {
    await Promise.resolve();
    throw new Error(message);
  };
}

/**
 * Arms the mock to fail the two calls one load makes — its attempt and its
 * retry — and no more.
 *
 * Bounded rather than left failing for the whole test: a standing failure would
 * also answer React's extra development-mode mount, whose rejection then settles
 * after the test has ended.
 */
function failsOneWholeLoad(message: string) {
  loadAudienceSegments
    .mockImplementationOnce(failsWith(message))
    .mockImplementationOnce(failsWith(message));
}

const { default: NewCampaignPage } =
  await import("@/app/(app)/campaigns/new/page");

const SEGMENT = { title: "Urban beginners", description: "New to climbing" };
const ONBOARDING_COPY = /names no audience segments yet/;
const LOAD_FAILED_COPY = /could not load your audience segments/;

/**
 * Fills a field the wizard requires before it will advance.
 *
 * Matched loosely because `Field` appends a `*` to the label of a required
 * field, so the accessible name is "Campaign name*" rather than the bare text.
 */
function fill(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(new RegExp(`^${label}`)), {
    target: { value },
  });
}

/**
 * Advances the wizard one step, awaiting the transition.
 *
 * `useWizard` moves asynchronously — it awaits a save before setting the step —
 * so the next step's fields are not in the DOM until that settles.
 */
async function clickNext() {
  fireEvent.click(screen.getByRole("button", { name: "Next →" }));
  await screen.findByText(/^Step/);
}

/**
 * Advances the wizard to the step that asks for the target audience segment,
 * which is the only step that shows them.
 */
async function goToSegmentStep() {
  fill("Campaign name", "Autumn push");
  fill("Primary business objective", "120 refill subscriptions");
  await clickNext();

  await waitFor(() => screen.getByLabelText(/^Business KPI/));
  fill("Business KPI", "120 subscriptions");
  fill("Marketing KPI", "2.5% conversion");
  fill("Creative KPI", "30% hook rate");
  await clickNext();
}

afterEach(cleanup);
beforeEach(() => loadAudienceSegments.mockReset());

describe("the new-campaign wizard's audience segments", () => {
  it("offers the segments the Brand DNA names", async () => {
    loadAudienceSegments.mockResolvedValue([SEGMENT]);
    render(<NewCampaignPage />);
    await goToSegmentStep();

    expect(await screen.findByText("Urban beginners")).toBeDefined();
    expect(screen.queryByText(ONBOARDING_COPY)).toBeNull();
  });

  it("says a Brand DNA that truly names no segments is the thing to fix", async () => {
    loadAudienceSegments.mockResolvedValue([]);
    render(<NewCampaignPage />);
    await goToSegmentStep();

    expect(await screen.findByText(ONBOARDING_COPY)).toBeDefined();
    expect(screen.queryByRole("button", { name: "Try again" })).toBeNull();
  });

  it("does not blame the Brand DNA when the fetch itself failed", async () => {
    failsOneWholeLoad("engine unreachable");
    render(<NewCampaignPage />);
    await goToSegmentStep();

    expect(await screen.findByText(LOAD_FAILED_COPY)).toBeDefined();
    // The whole point: an owner whose Brand DNA does name segments must never
    // be sent back to redo onboarding because a request failed.
    expect(screen.queryByText(ONBOARDING_COPY)).toBeNull();
  });

  it("retries once on its own before saying anything went wrong", async () => {
    loadAudienceSegments
      .mockImplementationOnce(failsWith("blip"))
      .mockResolvedValueOnce([SEGMENT]);
    render(<NewCampaignPage />);
    await goToSegmentStep();

    expect(await screen.findByText("Urban beginners")).toBeDefined();
    expect(screen.queryByText(LOAD_FAILED_COPY)).toBeNull();
    expect(loadAudienceSegments).toHaveBeenCalledTimes(2);
  });

  it("recovers in place when the owner retries, with no page reload", async () => {
    failsOneWholeLoad("engine unreachable");
    render(<NewCampaignPage />);
    await goToSegmentStep();

    const retry = await screen.findByRole("button", { name: "Try again" });
    loadAudienceSegments.mockResolvedValue([SEGMENT]);
    fireEvent.click(retry);

    expect(await screen.findByText("Urban beginners")).toBeDefined();
    expect(screen.queryByText(LOAD_FAILED_COPY)).toBeNull();
  });

  it("cannot be retried twice over, because the button goes while it loads", async () => {
    failsOneWholeLoad("engine unreachable");
    render(<NewCampaignPage />);
    await goToSegmentStep();

    const retry = await screen.findByRole("button", { name: "Try again" });
    loadAudienceSegments.mockReset();

    // A load held open, so the retry is still in flight when we look.
    let releaseTheLoad: () => void = () => {};
    const held = new Promise<AudienceSegment[]>((resolve) => {
      releaseTheLoad = () => resolve([SEGMENT]);
    });
    loadAudienceSegments.mockImplementation(() => held);
    fireEvent.click(retry);

    // The field goes back to loading, which takes the button with it — so a
    // second retry cannot be started on top of the first, and two loads cannot
    // race to answer the same field.
    expect(await screen.findByText("Loading your segments…")).toBeDefined();
    expect(screen.queryByRole("button", { name: "Try again" })).toBeNull();

    releaseTheLoad();
    expect(await screen.findByText("Urban beginners")).toBeDefined();
  });
});

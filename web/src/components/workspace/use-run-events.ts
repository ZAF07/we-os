"use client";

import { useEffect, useState } from "react";

export interface RunEvent {
  event: string;
  stage?: string;
  message?: string;
  outcome?: string;
}

export interface RunFeed {
  events: RunEvent[];
  finished: boolean;
  halted: boolean;
  disconnected: boolean;
  resuming: boolean;
}

const TERMINAL_EVENT = "run.summary";
const GATE_OUTCOME = "awaiting_approval";

/** The events after which the run is no longer working on the stage it started. */
const STAGE_ENDED = new Set([
  "stage.done",
  "stage.failed",
  "stage.blocked",
  "stage.quota_exhausted",
  TERMINAL_EVENT,
]);

const EMPTY: RunFeed = {
  events: [],
  finished: false,
  halted: false,
  disconnected: false,
  resuming: false,
};

/**
 * Names the stage a run is working on, read from what the stream has said.
 *
 * A stage is being worked on from its `stage.start` until the event that ends
 * that work — done, failed, blocked, out of credits, or the run's summary. A
 * revision starts the same stage again, so the answer follows the newest
 * start rather than the first.
 *
 * Args:
 *   events: The trace events seen so far, in order.
 *
 * Returns:
 *   The engine key of the stage being worked on, or null when none is.
 */
export function runningStage(events: RunEvent[]): string | null {
  let running: string | null = null;
  for (const event of events) {
    if (event.event === "stage.start") {
      running = event.stage ?? null;
    } else if (STAGE_ENDED.has(event.event)) {
      running = null;
    }
  }
  return running;
}

/**
 * Follows a run's live progress, replaying what it has already done.
 *
 * The engine's stream replays the trace from the top before following it live,
 * so a tab closed mid-run and reopened reattaches and sees the whole run rather
 * than only what happened after it came back. The stream closes itself on the
 * terminal event, which is what marks the feed finished.
 *
 * A dropped connection is reported as its own state, never as a finished run:
 * the two look identical from the browser's side, and telling a person their
 * run completed when the connection merely died would be a lie about their
 * campaign.
 *
 * A run that halts at a gate writes a summary saying so and ends its stream —
 * that is `halted`, distinct from finished, because the run is waiting on a
 * person rather than done. Approving or revising continues that *same* run,
 * so the page must attach again or it would never hear what happens next: the
 * version it asked for would land, and the screen would keep showing the one
 * it refused until someone reloaded. `attempt` is what says "this run has been
 * resumed"; changing it re-attaches. Until the re-attached stream replays, the
 * feed keeps showing what the run did before the gate, flagged `resuming`, so
 * the moment after a decision is not the moment the page goes blank.
 *
 * Args:
 *   runId: The run to follow, or null when nothing is in flight.
 *   attempt: Bumped each time the run is resumed, to re-attach the stream.
 *
 * Returns:
 *   The events seen so far; whether the run reached its terminal event, or
 *   halted at a gate; whether the connection dropped before either; and
 *   whether the run was resumed and the stream has not caught up yet.
 */
export function useRunEvents(runId: string | null, attempt = 0): RunFeed {
  const [feed, setFeed] = useState<{
    runId: string | null;
    attempt: number;
    events: RunEvent[];
    finished: boolean;
    halted: boolean;
    disconnected: boolean;
  }>({
    runId,
    attempt,
    events: [],
    finished: false,
    halted: false,
    disconnected: false,
  });

  useEffect(() => {
    if (runId === null) return;

    const source = new EventSource(`/api/runs/${runId}/stream`);
    source.onmessage = (message) => {
      const event = JSON.parse(message.data) as RunEvent;
      const summary = event.event === TERMINAL_EVENT;
      const finished = summary && event.outcome !== GATE_OUTCOME;
      setFeed((seen) => ({
        runId,
        attempt,
        events:
          seen.runId === runId && seen.attempt === attempt
            ? [...seen.events, event]
            : [event],
        finished,
        halted: summary && !finished,
        disconnected: false,
      }));
      if (finished) source.close();
    };
    source.onerror = () => {
      source.close();
      setFeed((seen) => ({
        ...seen,
        runId,
        attempt,
        disconnected: !seen.finished && !seen.halted,
      }));
    };
    return () => source.close();
  }, [runId, attempt]);

  if (feed.runId !== runId) return EMPTY;
  if (feed.attempt !== attempt) {
    return { ...EMPTY, events: feed.events, resuming: true };
  }
  return {
    events: feed.events,
    finished: feed.finished,
    halted: feed.halted,
    disconnected: feed.disconnected,
    resuming: false,
  };
}

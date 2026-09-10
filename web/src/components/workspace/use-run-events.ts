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

const EMPTY_FEED: RunFeed = {
  events: [],
  finished: false,
  halted: false,
  disconnected: false,
  resuming: false,
};

/**
 * What the hook holds between renders: the feed for one attachment, plus the
 * events the previous attachment had seen, so a resumed run's replay can be
 * told apart from what it does next.
 */
interface Attachment extends Omit<RunFeed, "resuming"> {
  runId: string | null;
  attempt: number;
  replayed: RunEvent[];
}

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
 * resumed"; changing it re-attaches.
 *
 * A re-attached stream replays everything the page already saw before it says
 * anything new. Until it has got past that, the feed keeps showing what the
 * run did before the gate, flagged `resuming` — so the moment after a decision
 * is not the moment the page goes blank, and the replay of the old gate is
 * not mistaken for the run halting again.
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
  const [feed, setFeed] = useState<Attachment>({
    runId,
    attempt,
    events: [],
    replayed: [],
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
      setFeed((seen) => {
        const sameRun = seen.runId === runId;
        const sameAttempt = sameRun && seen.attempt === attempt;
        return {
          runId,
          attempt,
          events: sameAttempt ? [...seen.events, event] : [event],
          replayed: sameAttempt ? seen.replayed : sameRun ? seen.events : [],
          finished,
          halted: summary && !finished,
          disconnected: false,
        };
      });
      if (finished) source.close();
    };
    source.onerror = () => {
      source.close();
      setFeed((seen) => {
        const sameAttempt = seen.runId === runId && seen.attempt === attempt;
        const ended = sameAttempt && (seen.finished || seen.halted);
        return {
          ...seen,
          runId,
          attempt,
          finished: sameAttempt && seen.finished,
          halted: sameAttempt && seen.halted,
          disconnected: !ended,
        };
      });
    };
    return () => source.close();
  }, [runId, attempt]);

  if (feed.runId !== runId) return EMPTY_FEED;
  if (feed.attempt !== attempt) {
    return { ...EMPTY_FEED, events: feed.events, resuming: true };
  }
  if (!feed.disconnected && feed.events.length <= feed.replayed.length) {
    return { ...EMPTY_FEED, events: feed.replayed, resuming: true };
  }
  return {
    events: feed.events,
    finished: feed.finished,
    halted: feed.halted,
    disconnected: feed.disconnected,
    resuming: false,
  };
}

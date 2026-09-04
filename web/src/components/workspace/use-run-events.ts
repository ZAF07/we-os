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
  disconnected: boolean;
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
 * A run that halts at a gate ends its stream — the trace has reached its
 * terminal event. Approving or revising continues that *same* run, so the page
 * must attach again or it would never hear what happens next: the version it
 * asked for would land, and the screen would keep showing the one it refused
 * until someone reloaded. `attempt` is what says "this run has been resumed";
 * changing it re-attaches.
 *
 * Args:
 *   runId: The run to follow, or null when nothing is in flight.
 *   attempt: Bumped each time the run is resumed, to re-attach the stream.
 *
 * Returns:
 *   The events seen so far, whether the run reached its terminal event, and
 *   whether the connection dropped before it did.
 */
export function useRunEvents(runId: string | null, attempt = 0): RunFeed {
  const [feed, setFeed] = useState<
    RunFeed & { runId: string | null; attempt: number }
  >({
    runId,
    attempt,
    events: [],
    finished: false,
    disconnected: false,
  });

  useEffect(() => {
    if (runId === null) return;

    const source = new EventSource(`/api/runs/${runId}/stream`);
    source.onmessage = (message) => {
      const event = JSON.parse(message.data) as RunEvent;
      setFeed((seen) => ({
        runId,
        attempt,
        events: seen.attempt === attempt ? [...seen.events, event] : [event],
        finished: event.event === "run.summary",
        disconnected: false,
      }));
      if (event.event === "run.summary") source.close();
    };
    source.onerror = () => {
      source.close();
      setFeed((seen) => ({
        ...seen,
        runId,
        attempt,
        disconnected: !seen.finished,
      }));
    };
    return () => source.close();
  }, [runId, attempt]);

  if (feed.runId !== runId || feed.attempt !== attempt) {
    return { events: [], finished: false, disconnected: false };
  }
  return {
    events: feed.events,
    finished: feed.finished,
    disconnected: feed.disconnected,
  };
}

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
 * Args:
 *   runId: The run to follow, or null when nothing is in flight.
 *
 * Returns:
 *   The events seen so far, whether the run reached its terminal event, and
 *   whether the connection dropped before it did.
 */
export function useRunEvents(runId: string | null): RunFeed {
  const [feed, setFeed] = useState<RunFeed & { runId: string | null }>({
    runId,
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
        events: [...seen.events, event],
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
        disconnected: !seen.finished,
      }));
    };
    return () => source.close();
  }, [runId]);

  if (feed.runId !== runId) {
    return { events: [], finished: false, disconnected: false };
  }
  return {
    events: feed.events,
    finished: feed.finished,
    disconnected: feed.disconnected,
  };
}

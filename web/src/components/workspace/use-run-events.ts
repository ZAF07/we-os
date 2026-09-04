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
}

/**
 * Follows a run's live progress, replaying what it has already done.
 *
 * The engine's stream replays the trace from the top before following it live,
 * so a tab closed mid-run and reopened reattaches and sees the whole run rather
 * than only what happened after it came back. The stream closes itself on the
 * terminal event, which is what marks the feed finished.
 *
 * Args:
 *   runId: The run to follow, or null when nothing is in flight.
 *
 * Returns:
 *   The events seen so far and whether the run has reached its terminal event.
 */
export function useRunEvents(runId: string | null): RunFeed {
  const [feed, setFeed] = useState<RunFeed & { runId: string | null }>({
    runId,
    events: [],
    finished: false,
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
      }));
      if (event.event === "run.summary") source.close();
    };
    source.onerror = () => {
      source.close();
      setFeed((seen) => ({ ...seen, runId, finished: true }));
    };
    return () => source.close();
  }, [runId]);

  if (feed.runId !== runId) {
    return { events: [], finished: false };
  }
  return { events: feed.events, finished: feed.finished };
}

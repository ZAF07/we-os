"use client";

import { stageTitle } from "@/lib/workspace";

import type { RunEvent } from "./use-run-events";

/**
 * The trace events worth showing a business owner, in their own words.
 *
 * A run trace records everything the engine did; most of it is machinery. Only
 * the events that answer "what is happening to my campaign right now" are
 * rendered — the rest are dropped rather than shown as raw event names.
 */
const EVENT_SENTENCES: Record<string, (event: RunEvent) => string> = {
  "gate.start": () => "Checking your Brand DNA and campaign goal.",
  "gate.passed": () => "Brand DNA and goal are complete.",
  "gate.failed": () => "Stopped: your Brand DNA or goal is incomplete.",
  "stage.start": (event) => `Working on ${named(event)}.`,
  "stage.review": (event) => `Reviewing ${named(event)} against its guardrail.`,
  "stage.done": (event) => `Finished ${named(event)}.`,
  "stage.approved": (event) => `You approved ${named(event)}.`,
  "stage.awaiting_clarification": (event) =>
    `${named(event)} has a question for you.`,
  "stage.clarified": (event) =>
    `You answered. ${named(event)} is starting again from your updated Brand DNA.`,
  "stage.revision_requested": (event) => `Revising ${named(event)}.`,
  "stage.blocked": (event) => `${named(event)} is waiting on an earlier stage.`,
  "stage.failed": (event) => `${named(event)} could not be completed.`,
  "stage.quota_exhausted": () => "Stopped: your credits are spent.",
};

/**
 * Names the stage an event is about, as the interface shows it.
 *
 * Args:
 *   event: The trace event.
 *
 * Returns:
 *   The stage's operator-facing title, or a neutral noun when it names none.
 */
function named(event: RunEvent): string {
  return event.stage ? stageTitle(event.stage) : "this stage";
}

/**
 * Describes one trace event in a sentence, or nothing if it is machinery.
 *
 * Args:
 *   event: The trace event.
 *
 * Returns:
 *   The sentence to render, or null to drop the event.
 */
export function describeEvent(event: RunEvent): string | null {
  const sentence = EVENT_SENTENCES[event.event];
  return sentence ? sentence(event) : null;
}

/**
 * Reads the outcome of the newest run summary the stream has replayed.
 *
 * Args:
 *   events: The trace events seen so far.
 *
 * Returns:
 *   The outcome, or null when the run has not summarised yet.
 */
function lastSummaryOutcome(events: RunEvent[]): string | null {
  for (let index = events.length - 1; index >= 0; index -= 1) {
    if (events[index].event === "run.summary") {
      return events[index].outcome ?? null;
    }
  }
  return null;
}

/**
 * Renders a run's live progress as it happens.
 *
 * A dropped connection is shown as exactly that, never as a finished run: the
 * work may well still be going, and the honest thing is to say the page stopped
 * hearing about it and how to catch up.
 *
 * A run halted at a gate, or on a question for the owner, is neither working
 * nor finished: it is waiting on the person reading this, and the header says
 * which of the two it is waiting for.
 *
 * Args:
 *   events: The trace events seen so far.
 *   finished: Whether the run has reached its terminal event.
 *   halted: Whether the run is holding on a person.
 *   disconnected: Whether the stream dropped before the run finished.
 */
export function RunProgress({
  events,
  finished,
  halted,
  disconnected,
}: {
  events: RunEvent[];
  finished: boolean;
  halted: boolean;
  disconnected: boolean;
}) {
  const lines = events
    .map((event, index) => ({ index, text: describeEvent(event) }))
    .filter(
      (line): line is { index: number; text: string } => line.text !== null,
    );

  if (lines.length === 0 && (finished || halted)) return null;

  const working = !finished && !halted;
  const asking = lastSummaryOutcome(events) === "awaiting_clarification";

  if (disconnected) {
    return (
      <div
        role="alert"
        className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3.5"
      >
        <div className="text-[11px] font-bold tracking-wide text-amber-800 uppercase">
          Lost the live feed
        </div>
        <p className="mt-1 text-[12.5px] text-amber-900">
          The run may still be going. Reload the page to reattach to it.
        </p>
      </div>
    );
  }

  return (
    <div
      role="log"
      aria-label="Run progress"
      className="rounded-xl border border-indigo-200 bg-indigo-50 px-4 py-3.5"
    >
      <div className="flex items-center gap-2 text-[11px] font-bold tracking-wide text-indigo-700 uppercase">
        {working && (
          <span className="size-2 animate-pulse rounded-full bg-indigo-600" />
        )}
        {finished
          ? "Run finished"
          : halted
            ? asking
              ? "Waiting for your answer"
              : "Waiting for your decision"
            : "Working"}
      </div>
      <ol className="mt-2 flex flex-col gap-1 text-[12.5px] text-indigo-900">
        {lines.slice(-8).map((line) => (
          <li key={line.index}>{line.text}</li>
        ))}
      </ol>
    </div>
  );
}

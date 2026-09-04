"use client";

import { StatusPill } from "@/components/ui/status-pill";
import type { DeliverableVersionSummary } from "@/lib/engine";
import { cn } from "@/lib/utils";

/**
 * Renders a deliverable's markdown as the business owner reads it.
 *
 * The engine writes markdown, and the interface shows it whole. Nothing is
 * summarised or truncated: the decision at the gate is about this document, so
 * hiding part of it would ask for a decision on something the person cannot see.
 *
 * Args:
 *   content: The deliverable's full markdown.
 */
export function DeliverableContent({ content }: { content: string }) {
  return (
    <article
      aria-label="Deliverable"
      className="rounded-xl border bg-card px-[22px] py-5 text-[13.5px] leading-relaxed whitespace-pre-wrap text-slate-800"
    >
      {content}
    </article>
  );
}

/**
 * Renders the banner marking a deliverable as resting on a superseded decision.
 *
 * The re-run control lives here because staleness is the owner's to resolve:
 * the flag and the one action that clears it belong together, and nothing
 * re-runs until they ask for it (ADR-0015).
 *
 * Args:
 *   onRerun: Starts a run to bring the stage up to date.
 *   pending: Whether a re-run is already in flight.
 */
export function StaleBanner({
  onRerun,
  pending,
}: {
  onRerun: () => void;
  pending: boolean;
}) {
  return (
    <div
      role="status"
      className="mb-4 flex flex-wrap items-center gap-2 rounded-xl border border-orange-200 bg-orange-50 px-4 py-3"
    >
      <StatusPill status="Stale" />
      <span className="flex-1 text-[12.5px] text-orange-900">
        Built on a decision that has since been re-opened. Re-run this stage to
        bring it up to date — it will not update on its own.
      </span>
      <button
        onClick={onRerun}
        disabled={pending}
        className="cursor-pointer rounded-lg border border-orange-300 bg-card px-2.5 py-[5px] text-xs font-semibold text-orange-800 hover:bg-orange-100 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {pending ? "Starting…" : "Re-run this stage"}
      </button>
    </div>
  );
}

/**
 * Renders a deliverable's version history, newest first.
 *
 * Each entry names the feedback that produced it and whether that came from a
 * person or the QA reviewer, so the history explains itself months later
 * (ADR-0015). Selecting a version shows it, which is how two versions are
 * compared.
 *
 * Args:
 *   versions: The version summaries, newest first.
 *   selected: The version currently shown.
 *   onSelect: Shows a version.
 */
export function VersionHistory({
  versions,
  selected,
  onSelect,
}: {
  versions: DeliverableVersionSummary[];
  selected: number | null;
  onSelect: (version: number) => void;
}) {
  if (versions.length === 0) return null;

  return (
    <section aria-label="Version history" className="mt-[18px]">
      <div className="mb-2 text-[11px] font-bold tracking-wide text-muted-foreground uppercase">
        Version history
      </div>
      <ol className="flex flex-col gap-1.5">
        {versions.map((version) => (
          <li key={version.version}>
            <button
              onClick={() => onSelect(version.version)}
              aria-current={selected === version.version ? "true" : undefined}
              className={cn(
                "w-full cursor-pointer rounded-[10px] border px-3 py-2.5 text-left hover:border-indigo-200",
                selected === version.version && "border-primary bg-indigo-50",
              )}
            >
              <div className="flex items-center gap-1.5">
                <span className="text-[12.5px] font-bold">
                  v{version.version}
                </span>
                <span className="text-[11px] text-muted-foreground">
                  {new Date(version.created_at).toLocaleString()}
                </span>
              </div>
              <div className="mt-0.5 text-[12px] text-slate-700">
                {version.feedback
                  ? `${sourceLabel(version.feedback_source)}: ${version.feedback}`
                  : "First draft — nothing prompted it."}
              </div>
            </button>
          </li>
        ))}
      </ol>
    </section>
  );
}

/**
 * Names who asked for a revision, in the operator's terms.
 *
 * Args:
 *   source: The engine's feedback source.
 *
 * Returns:
 *   Who the feedback came from.
 */
function sourceLabel(source: string | null): string {
  if (source === "human") return "You asked";
  if (source === "reviewer") return "Guardrail review";
  return "Revised";
}

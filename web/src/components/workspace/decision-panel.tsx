"use client";

import { useState } from "react";

/**
 * Renders the Approval Gate: approve the deliverable, or send it back.
 *
 * The gate is the point of the product — it is what makes we-OS a
 * decision-making system rather than a generator — so both choices are offered
 * plainly, and sending back requires written feedback because a refusal with
 * nothing to act on would re-run the stage identically and charge for it
 * (ADR-0015).
 *
 * Args:
 *   stageName: The stage being decided, as the interface names it.
 *   onApprove: Approves the deliverable and resumes the run.
 *   onRevise: Sends the deliverable back with feedback.
 *   pending: Whether a decision is already being sent.
 */
export function ApprovalGate({
  stageName,
  onApprove,
  onRevise,
  pending,
}: {
  stageName: string;
  onApprove: () => void;
  onRevise: (feedback: string) => void;
  pending: boolean;
}) {
  const [revising, setRevising] = useState(false);
  const [feedback, setFeedback] = useState("");

  return (
    <div className="rounded-xl border border-indigo-200 bg-indigo-50 px-4 py-3.5">
      <div className="text-[11px] font-bold tracking-wide text-indigo-700 uppercase">
        Decision required
      </div>
      <div className="mt-1 text-sm font-bold">Approve {stageName}</div>
      <div className="mt-2 rounded-lg border border-indigo-200 bg-card px-2.5 py-2 text-xs text-indigo-700">
        Approving continues the run into the next stage. Sending it back
        produces a new version — the one you refused stays readable.
      </div>

      {revising ? (
        <div className="mt-3">
          <label
            htmlFor="revision-feedback"
            className="block text-xs font-semibold text-indigo-900"
          >
            What do you want changed?
          </label>
          <textarea
            id="revision-feedback"
            value={feedback}
            onChange={(event) => setFeedback(event.target.value)}
            rows={4}
            className="mt-1.5 w-full rounded-lg border border-indigo-200 bg-card px-2.5 py-2 text-[12.5px]"
          />
          <div className="mt-2 flex gap-2">
            <button
              onClick={() => onRevise(feedback.trim())}
              disabled={pending || feedback.trim() === ""}
              className="flex-1 cursor-pointer rounded-lg bg-primary py-2 text-[13px] font-semibold text-primary-foreground hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {pending ? "Sending…" : "Send back"}
            </button>
            <button
              onClick={() => setRevising(false)}
              disabled={pending}
              className="cursor-pointer rounded-lg border border-indigo-200 bg-card px-3 py-2 text-[13px] font-semibold hover:bg-slate-50"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div className="mt-3 flex gap-2">
          <button
            onClick={onApprove}
            disabled={pending}
            className="flex-1 cursor-pointer rounded-lg bg-primary py-2 text-[13px] font-semibold text-primary-foreground hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {pending ? "Approving…" : "Approve"}
          </button>
          <button
            onClick={() => setRevising(true)}
            disabled={pending}
            className="flex-1 cursor-pointer rounded-lg border border-indigo-200 bg-card py-2 text-[13px] font-semibold hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
          >
            Request changes
          </button>
        </div>
      )}
    </div>
  );
}

/**
 * Renders the panel for a stage the owner already approved.
 *
 * Re-opening is distinct from a revision at a gate: it returns to a decision
 * already made, re-runs that stage alone, and marks everything downstream Stale
 * rather than regenerating it (ADR-0015). Feedback is required for the same
 * reason a revision needs it.
 *
 * Args:
 *   stageName: The approved stage, as the interface names it.
 *   onReopen: Re-opens the stage with the owner's feedback.
 *   pending: Whether a re-open is already being sent.
 */
export function ApprovedPanel({
  stageName,
  onReopen,
  pending,
}: {
  stageName: string;
  onReopen: (feedback: string) => void;
  pending: boolean;
}) {
  const [reopening, setReopening] = useState(false);
  const [feedback, setFeedback] = useState("");

  return (
    <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3.5">
      <div className="text-[13.5px] font-bold text-emerald-700">
        ✓ {stageName} approved
      </div>
      <div className="mt-1 text-[12.5px] text-emerald-800">
        Everything after this stage was built on it. Re-opening it flags that
        work as stale — nothing is regenerated until you ask.
      </div>

      {reopening ? (
        <div className="mt-3">
          <label
            htmlFor="reopen-feedback"
            className="block text-xs font-semibold text-emerald-900"
          >
            What do you want changed?
          </label>
          <textarea
            id="reopen-feedback"
            value={feedback}
            onChange={(event) => setFeedback(event.target.value)}
            rows={4}
            className="mt-1.5 w-full rounded-lg border border-emerald-200 bg-card px-2.5 py-2 text-[12.5px]"
          />
          <div className="mt-2 flex gap-2">
            <button
              onClick={() => onReopen(feedback.trim())}
              disabled={pending || feedback.trim() === ""}
              className="flex-1 cursor-pointer rounded-lg bg-orange-600 py-2 text-[13px] font-semibold text-white hover:bg-orange-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {pending ? "Re-opening…" : "Re-open"}
            </button>
            <button
              onClick={() => setReopening(false)}
              disabled={pending}
              className="cursor-pointer rounded-lg border border-emerald-200 bg-card px-3 py-2 text-[13px] font-semibold hover:bg-slate-50"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setReopening(true)}
          disabled={pending}
          className="mt-2.5 cursor-pointer rounded-lg border border-orange-200 bg-card px-2.5 py-[5px] text-xs font-semibold text-orange-800 hover:bg-orange-50 disabled:cursor-not-allowed disabled:opacity-60"
        >
          Re-open this decision
        </button>
      )}
    </div>
  );
}

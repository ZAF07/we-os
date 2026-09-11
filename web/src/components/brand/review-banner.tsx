"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import type { DnaReview } from "@/lib/engine";

/**
 * Asks the business to look over its Brand DNA when a review is due, and
 * offers the Reviewed action that says it did.
 *
 * Nothing is rendered when no review is due, so the Brand page reads as it
 * always has for a business that looked recently. Clicking Reviewed records
 * the review and hides the banner at once; the page then refreshes from the
 * server, whose own read wins from there. The banner remembers which review
 * it dismissed rather than that it was dismissed, so the next one due is
 * shown again (ADR-0028).
 *
 * Args:
 *   review: Whether a review is due and when the last one was, or null when
 *     that could not be read — which shows nothing, as no review does.
 *   markReviewed: Records the review.
 */
export function ReviewBanner({
  review,
  markReviewed,
}: {
  review: DnaReview | null;
  markReviewed: () => Promise<DnaReview>;
}) {
  const router = useRouter();
  const [dismissed, setDismissed] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startMarking] = useTransition();

  if (review === null || !review.due) return null;
  if (dismissed !== null && dismissed === review.reviewed_at) return null;

  const mark = () => {
    setError(null);
    startMarking(async () => {
      try {
        await markReviewed();
        setDismissed(review.reviewed_at);
        router.refresh();
      } catch {
        setError("Could not mark it reviewed. Try again.");
      }
    });
  };

  return (
    <section
      aria-label="Brand DNA review"
      className="mb-4 flex flex-wrap items-center gap-3 rounded-xl border border-amber-200 bg-amber-50 px-[18px] py-3"
    >
      <div className="min-w-[220px] flex-1">
        <div className="text-[13.5px] font-semibold text-amber-900">
          Time to look over your Brand DNA
        </div>
        <p className="mt-0.5 text-[12.5px] text-amber-800">
          Facts drift. Check these answers and your Clarifications still hold,
          correct any that do not, then mark it reviewed. Every later campaign
          is grounded in what is written here.
        </p>
        {error && (
          <p role="alert" className="mt-1 text-[12.5px] text-red-800">
            {error}
          </p>
        )}
      </div>
      <button
        onClick={mark}
        disabled={pending}
        className="shrink-0 cursor-pointer rounded-lg bg-amber-800 px-3 py-1.5 text-[12.5px] font-semibold text-white hover:bg-amber-900 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {pending ? "Saving…" : "Reviewed"}
      </button>
    </section>
  );
}

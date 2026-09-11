import { BrandScreen } from "@/components/brand/brand-screen";
import {
  engineErrorMessage,
  getDnaReview,
  nullOnEngineError,
  type DnaReview,
} from "@/lib/engine";

import { loadOnboarding } from "../onboarding/actions";

export const dynamic = "force-dynamic";

/**
 * Renders the Brand screen from the tenant's real Brand DNA.
 *
 * Loaded on the server, from the same reads onboarding uses — the Brand DNA is
 * one thing, whether a business is first authoring it or later correcting it.
 * Whether it is due a review is read alongside, and is optional: a failed read
 * costs the review banner, not the screen.
 */
export default async function BrandPage() {
  let state;
  let review: DnaReview | null;
  try {
    [state, review] = await Promise.all([
      loadOnboarding(),
      getDnaReview().catch(nullOnEngineError),
    ]);
  } catch (error) {
    return (
      <main className="flex-1 overflow-y-auto px-4 py-6 md:px-8 md:py-7">
        <h1 className="text-xl font-bold tracking-tight">Brand</h1>
        <p role="alert" className="mt-2 text-[13px] text-muted-foreground">
          {engineErrorMessage(error)}
        </p>
      </main>
    );
  }

  return (
    <BrandScreen
      questionnaire={state.questionnaire}
      dna={state.dna}
      completeness={state.completeness}
      review={review}
    />
  );
}

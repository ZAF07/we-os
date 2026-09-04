import { BrandScreen } from "@/components/brand/brand-screen";
import { EngineError } from "@/lib/engine";

import { loadOnboarding } from "../onboarding/actions";

export const dynamic = "force-dynamic";

/**
 * Renders the Brand screen from the tenant's real Brand DNA.
 *
 * Loaded on the server, from the same reads onboarding uses — the Brand DNA is
 * one thing, whether a business is first authoring it or later correcting it.
 */
export default async function BrandPage() {
  let state;
  try {
    state = await loadOnboarding();
  } catch (error) {
    const message =
      error instanceof EngineError
        ? error.message
        : "Could not reach the engine. Is it running on ENGINE_BASE_URL?";
    return (
      <main className="flex-1 overflow-y-auto px-4 py-6 md:px-8 md:py-7">
        <h1 className="text-xl font-bold tracking-tight">Brand</h1>
        <p role="alert" className="mt-2 text-[13px] text-muted-foreground">
          {message}
        </p>
      </main>
    );
  }

  return (
    <BrandScreen
      questionnaire={state.questionnaire}
      dna={state.dna}
      completeness={state.completeness}
    />
  );
}

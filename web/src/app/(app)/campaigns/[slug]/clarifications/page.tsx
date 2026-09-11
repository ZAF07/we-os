import Link from "next/link";

import { ClarificationsForm } from "@/components/workspace/clarifications-form";
import { engineErrorMessage } from "@/lib/engine";

import { answerClarificationsAction, loadClarifications } from "./actions";

export const dynamic = "force-dynamic";

/**
 * Renders the questions a specialist stopped to ask the business owner.
 *
 * Reached from the Decision item on Home and from the Workspace. The owner
 * answers them all here; the answers join their Brand DNA and the run
 * continues on its own (ADR-0028).
 *
 * Args:
 *   props: The route params carrying the campaign slug.
 */
export default async function ClarificationsPage(props: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await props.params;

  let view;
  try {
    view = await loadClarifications(slug);
  } catch (error) {
    return <EngineDown error={error} />;
  }

  if (view === null) return <NotFound />;

  return (
    <main className="flex-1 overflow-y-auto px-4 py-6 md:px-8 md:py-7">
      <div className="flex flex-wrap items-center gap-2 text-[12.5px] text-muted-foreground">
        <Link href="/campaigns" className="hover:text-primary">
          Campaigns
        </Link>
        <span>/</span>
        <Link href={`/campaigns/${slug}`} className="hover:text-primary">
          {view.campaign.name}
        </Link>
        <span>/</span>
        <span className="font-semibold text-foreground">Questions</span>
      </div>
      <h1 className="mt-3 text-[22px] font-bold tracking-tight">
        Questions for you
      </h1>
      {view.pending === null ? (
        <NothingAsked slug={slug} />
      ) : (
        <ClarificationsForm
          slug={slug}
          pending={view.pending}
          submit={answerClarificationsAction}
        />
      )}
    </main>
  );
}

/**
 * Renders the page when the campaign's run is not asking anything.
 *
 * Args:
 *   slug: The campaign slug, for the way back.
 */
function NothingAsked({ slug }: { slug: string }) {
  return (
    <div className="mt-2 max-w-[720px]">
      <p className="text-[13px] text-muted-foreground">
        Nothing is waiting on an answer for this campaign right now.
      </p>
      <p className="mt-3 text-[13px]">
        <Link
          href={`/campaigns/${slug}`}
          className="font-semibold text-primary"
        >
          ← Back to the campaign
        </Link>
      </p>
    </div>
  );
}

/** Renders the page for a slug the tenant does not own — or that never existed. */
function NotFound() {
  return (
    <main className="flex-1 overflow-y-auto px-4 py-6 md:px-8 md:py-7">
      <h1 className="text-[22px] font-bold tracking-tight">
        Campaign not found
      </h1>
      <p className="mt-1 text-[13px] text-muted-foreground">
        <Link href="/campaigns">← Back to campaigns</Link>
      </p>
    </main>
  );
}

/**
 * Renders the page when the engine could not answer.
 *
 * Args:
 *   error: What went wrong reaching the engine.
 */
function EngineDown({ error }: { error: unknown }) {
  return (
    <main className="flex-1 overflow-y-auto px-4 py-6 md:px-8 md:py-7">
      <h1 className="text-[22px] font-bold tracking-tight">
        Cannot load these questions
      </h1>
      <p role="alert" className="mt-1 text-[13px] text-muted-foreground">
        {engineErrorMessage(error)}
      </p>
      <p className="mt-3 text-[13px]">
        <Link href="/campaigns">← Back to campaigns</Link>
      </p>
    </main>
  );
}

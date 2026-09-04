import Link from "next/link";

import { Workspace } from "@/components/workspace/workspace";
import { EngineError } from "@/lib/engine";

import { loadWorkspace } from "./actions";

export const dynamic = "force-dynamic";

/**
 * Renders the campaign Workspace — the screen where the product happens.
 *
 * Loaded on the server so the first paint already carries the campaign's real
 * stages and lifecycle status; the interaction that follows is the client
 * Workspace's.
 *
 * Args:
 *   props: The route params carrying the campaign slug.
 */
export default async function CampaignWorkspacePage(props: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await props.params;

  let snapshot;
  try {
    snapshot = await loadWorkspace(slug);
  } catch (error) {
    return <EngineDown error={error} />;
  }

  if (snapshot === null) return <NotFound />;

  return <Workspace campaign={snapshot.campaign} runId={snapshot.runId} />;
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
  const message =
    error instanceof EngineError
      ? error.message
      : "Could not reach the engine. Is it running on ENGINE_BASE_URL?";
  return (
    <main className="flex-1 overflow-y-auto px-4 py-6 md:px-8 md:py-7">
      <h1 className="text-[22px] font-bold tracking-tight">
        Cannot load this campaign
      </h1>
      <p role="alert" className="mt-1 text-[13px] text-muted-foreground">
        {message}
      </p>
      <p className="mt-3 text-[13px]">
        <Link href="/campaigns">← Back to campaigns</Link>
      </p>
    </main>
  );
}

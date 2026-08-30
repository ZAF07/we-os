import Link from "next/link";
import { AlertCircle, CheckCircle2, FileText } from "lucide-react";

import { Card, CardHeader } from "@/components/ui/card";
import {
  EngineError,
  getDeliverable,
  getDeliverables,
  getGate,
  getMe,
  type Deliverable,
  type DeliverableFile,
  type GateReport,
  type Me,
} from "@/lib/engine";

export const dynamic = "force-dynamic";

/**
 * The campaign this tracer screen reads. Slices 10–12 wire campaign selection;
 * until then the workspace proves the round trip against one known slug.
 */
const CAMPAIGN_SLUG = "acme";

interface WorkspaceData {
  me: Me;
  gate: GateReport;
  files: DeliverableFile[];
  preview: Deliverable | null;
}

/**
 * Loads everything the workspace renders, in one place.
 *
 * A campaign the tenant does not own answers 404 exactly as a missing one does,
 * so an empty deliverable list is the correct rendering for both.
 *
 * Returns:
 *   The identity, gate report, deliverable list and first deliverable's content,
 *   or an error message to show.
 */
async function loadWorkspace(): Promise<WorkspaceData | { error: string }> {
  try {
    const [me, gate] = await Promise.all([getMe(), getGate(CAMPAIGN_SLUG)]);
    let files: DeliverableFile[] = [];
    try {
      files = (await getDeliverables(CAMPAIGN_SLUG)).files;
    } catch (error) {
      if (!(error instanceof EngineError && error.status === 404)) throw error;
    }
    const first = files.find((file) => file.name !== "goal.md") ?? files[0];
    const preview = first ? await getDeliverable(CAMPAIGN_SLUG, first.name) : null;
    return { me, gate, files, preview };
  } catch (error) {
    const message =
      error instanceof EngineError
        ? `${error.type}: ${error.message}`
        : "Could not reach the engine. Is it running on ENGINE_BASE_URL?";
    return { error: message };
  }
}

/** Renders the Brand DNA completeness report from the Stage 0 gate. */
function GateCard({ gate }: { gate: GateReport }) {
  return (
    <Card>
      <CardHeader
        title="Brand DNA completeness"
        action={
          <span
            className={
              gate.ok
                ? "rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700"
                : "rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-semibold text-amber-700"
            }
          >
            {gate.ok ? "Ready" : "Incomplete"}
          </span>
        }
      />
      <div className="px-4 pb-4">
        {gate.ok ? (
          <p className="flex items-center gap-2 text-sm text-emerald-700">
            <CheckCircle2 className="size-4 shrink-0" />
            Every Required field is filled. Work can begin.
          </p>
        ) : (
          <>
            <p className="mb-3 flex items-center gap-2 text-sm text-amber-700">
              <AlertCircle className="size-4 shrink-0" />
              {gate.issues.length} item{gate.issues.length === 1 ? "" : "s"} stand
              between you and starting work.
            </p>
            <ul className="space-y-1.5">
              {gate.issues.map((issue) => (
                <li
                  key={issue}
                  className="rounded-md bg-slate-50 px-3 py-2 text-[13px] text-slate-700"
                >
                  {issue}
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </Card>
  );
}

/** Renders the markdown of one deliverable, proving it can be read back. */
function DeliverablePreview({ deliverable }: { deliverable: Deliverable }) {
  return (
    <Card>
      <CardHeader title={deliverable.name} />
      <div className="px-4 pb-4">
        <pre className="max-h-96 overflow-auto rounded-md bg-slate-50 px-3 py-2.5 font-mono text-[12px] leading-relaxed whitespace-pre-wrap text-slate-700">
          {deliverable.content}
        </pre>
      </div>
    </Card>
  );
}

/** Renders the campaign's written deliverables. */
function DeliverablesCard({ files }: { files: DeliverableFile[] }) {
  return (
    <Card>
      <CardHeader title={`Deliverables — ${CAMPAIGN_SLUG}`} />
      <div className="px-4 pb-4">
        {files.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Nothing written yet. Start a run to produce the first deliverable.
          </p>
        ) : (
          <ul className="space-y-1.5">
            {files.map((file) => (
              <li
                key={file.path}
                className="flex items-center gap-2.5 rounded-md bg-slate-50 px-3 py-2 text-[13px]"
              >
                <FileText className="size-4 shrink-0 text-slate-400" />
                <span className="font-medium">{file.name}</span>
                <span className="ml-auto font-mono text-[11.5px] text-muted-foreground">
                  {file.path}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Card>
  );
}

/**
 * The authenticated round trip: sign-in → verified token → engine → tenant data.
 *
 * Everything on this page comes from the engine, scoped to the tenant derived
 * from the caller's verified claim — nothing is mocked and no business identity
 * is sent.
 */
export default async function WorkspacePage() {
  const data = await loadWorkspace();

  if ("error" in data) {
    return (
      <main className="flex-1 overflow-y-auto p-6">
        <Card>
          <CardHeader title="Engine unavailable" />
          <div className="px-4 pb-4 text-sm text-muted-foreground">
            <p>{data.error}</p>
            <p className="mt-2">
              Start it with{" "}
              <code className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[12px]">
                make api
              </code>{" "}
              in <code className="font-mono text-[12px]">agent-harness/</code>.
            </p>
          </div>
        </Card>
      </main>
    );
  }

  return (
    <main className="flex-1 space-y-4 overflow-y-auto p-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">
          {data.me.business_name}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Signed in as {data.me.email ?? data.me.user_id}. Everything below is
          scoped to your business by the engine.
        </p>
      </div>

      <GateCard gate={data.gate} />
      <DeliverablesCard files={data.files} />
      {data.preview && <DeliverablePreview deliverable={data.preview} />}

      <p className="text-xs text-muted-foreground">
        Read the full campaign view in{" "}
        <Link href="/campaigns" className="underline underline-offset-2">
          Campaigns
        </Link>
        .
      </p>
    </main>
  );
}

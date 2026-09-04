"use server";

import { revalidatePath } from "next/cache";

import {
  approveStage,
  getCampaign,
  getDeliverableVersion,
  getDeliverableVersions,
  getStageDeliverable,
  listActiveRuns,
  reopenStage,
  reviseStage,
  startRun,
  EngineError,
  type Campaign,
  type DeliverableVersionDetail,
  type DeliverableVersionSummary,
  type StageDeliverable,
} from "@/lib/engine";
import { deliverableName } from "@/lib/workspace";

export interface WorkspaceSnapshot {
  campaign: Campaign;
  runId: string | null;
}

export interface StageView {
  deliverable: StageDeliverable | null;
  versions: DeliverableVersionSummary[];
}

export interface ActionResult {
  error: string | null;
}

/**
 * Turns an engine failure into the message the Workspace shows.
 *
 * The engine explains a refusal in the operator's terms, so its message is
 * surfaced as-is rather than replaced by a generic one. Two refusals carry
 * detail the message alone leaves out, and both are the kind a person can act
 * on, so the numbers are put back:
 *
 * - A failed **DNA Gate** says only that the gate failed; what the person needs
 *   is the list of fields it named.
 * - An **exhausted allowance** says work has stopped; what they need is how far
 *   past the line they are, since that is what tells them whether to wait for a
 *   renewal or ask for more (ADR-0020).
 *
 * Args:
 *   error: The failure raised while calling the engine.
 *
 * Returns:
 *   The message to render.
 *
 * Throws:
 *   Error: Anything that is not an engine failure, which is a real fault.
 */
function engineMessage(error: unknown): string {
  if (!(error instanceof EngineError)) throw error;

  const missing = error.detail.missing_fields;
  if (Array.isArray(missing) && missing.length > 0) {
    return `${error.message} Still needed: ${missing.join("; ")}`;
  }

  if (error.type === "quota_exhausted") {
    const { used, allowance } = error.detail;
    if (typeof used === "number" && typeof allowance === "number") {
      return `${error.message} You have used ${used.toFixed(2)} of ${allowance.toFixed(2)}.`;
    }
  }

  return error.message;
}

/**
 * Loads a campaign and the id of the run currently working on it, if any.
 *
 * Args:
 *   slug: The campaign slug.
 *
 * Returns:
 *   The campaign and its live run id, or null when the tenant owns no such
 *   campaign — which is also what another tenant's campaign answers.
 */
export async function loadWorkspace(
  slug: string,
): Promise<WorkspaceSnapshot | null> {
  let campaign: Campaign;
  try {
    campaign = await getCampaign(slug);
  } catch (error) {
    if (error instanceof EngineError && error.status === 404) return null;
    throw error;
  }
  const { runs } = await listActiveRuns();
  const active = runs.find((run) => run.slug === slug);
  return { campaign, runId: active?.run_id ?? null };
}

/**
 * Loads one stage's latest deliverable and its version history.
 *
 * A stage that has produced nothing is not an error — it is the ordinary state
 * of work that has not run yet — so it answers an empty view rather than
 * throwing.
 *
 * Args:
 *   slug: The campaign slug.
 *   stageKey: The stage to read.
 *
 * Returns:
 *   The deliverable and its versions, both empty when the stage has not run.
 */
export async function loadStage(
  slug: string,
  stageKey: string,
): Promise<StageView> {
  const name = deliverableName(stageKey);
  try {
    const [deliverable, history] = await Promise.all([
      getStageDeliverable(slug, name),
      getDeliverableVersions(slug, name),
    ]);
    return { deliverable, versions: history.versions };
  } catch (error) {
    if (error instanceof EngineError && error.status === 404) {
      return { deliverable: null, versions: [] };
    }
    throw error;
  }
}

/**
 * Loads one historical version of a stage's deliverable, for comparison.
 *
 * Args:
 *   slug: The campaign slug.
 *   stageKey: The stage the version belongs to.
 *   version: The version number to read.
 *
 * Returns:
 *   The version's full content and the feedback behind it, or null when the
 *   tenant has no such version.
 */
export async function loadVersion(
  slug: string,
  stageKey: string,
  version: number,
): Promise<DeliverableVersionDetail | null> {
  try {
    return await getDeliverableVersion(
      slug,
      deliverableName(stageKey),
      version,
    );
  } catch (error) {
    if (error instanceof EngineError && error.status === 404) return null;
    throw error;
  }
}

/**
 * Runs one engine call that changes a campaign, then refreshes what it touched.
 *
 * Every such call shares the same shape: do the thing, invalidate the screens
 * that show the campaign, and hand back the engine's own words if it refuses.
 * The Workspace, the campaigns list and Home all read the same state, so a
 * decision made here must show up on all three.
 *
 * Args:
 *   slug: The campaign the call acts on.
 *   call: The engine call to make.
 *
 * Returns:
 *   Nothing on success, or the engine's reason for refusing.
 */
async function changeCampaign(
  slug: string,
  call: () => Promise<unknown>,
): Promise<ActionResult> {
  try {
    await call();
    revalidatePath(`/campaigns/${slug}`);
    revalidatePath("/campaigns");
    revalidatePath("/");
    return { error: null };
  } catch (error) {
    return { error: engineMessage(error) };
  }
}

/**
 * Starts a run of the campaign's pipeline, or of one stage alone.
 *
 * Clearing a stale deliverable runs only the stage that is stale: re-running
 * the whole pipeline would redo work nobody asked to have redone, and charge
 * for it (ADR-0015).
 *
 * Args:
 *   slug: The campaign slug.
 *   stageKey: The single stage to run, or null for the whole pipeline.
 *
 * Returns:
 *   Nothing on success, or the engine's reason for refusing — an incomplete
 *   Brand DNA, a spent allowance, a run already in flight.
 */
export async function startRunAction(
  slug: string,
  stageKey: string | null = null,
): Promise<ActionResult> {
  return changeCampaign(slug, () => startRun(slug, stageKey));
}

/**
 * Approves the stage a run is halted at, resuming it into the next stage.
 *
 * Args:
 *   slug: The campaign slug, for revalidation.
 *   runId: The halted run.
 *   stageKey: The stage being approved.
 *
 * Returns:
 *   Nothing on success, or the engine's reason for refusing.
 */
export async function approveStageAction(
  slug: string,
  runId: string,
  stageKey: string,
): Promise<ActionResult> {
  return changeCampaign(slug, () => approveStage(runId, stageKey));
}

/**
 * Sends the waiting stage back with feedback, producing a new version.
 *
 * Args:
 *   slug: The campaign slug, for revalidation.
 *   runId: The halted run.
 *   stageKey: The stage being sent back.
 *   feedback: What the business owner wants changed.
 *
 * Returns:
 *   Nothing on success, or the engine's reason for refusing.
 */
export async function reviseStageAction(
  slug: string,
  runId: string,
  stageKey: string,
  feedback: string,
): Promise<ActionResult> {
  return changeCampaign(slug, () => reviseStage(runId, stageKey, feedback));
}

/**
 * Re-opens an approved stage, re-running it and marking downstream work stale.
 *
 * Args:
 *   slug: The campaign slug.
 *   stageKey: The stage to re-open.
 *   feedback: What the owner wants changed.
 *
 * Returns:
 *   Nothing on success, or the engine's reason for refusing.
 */
export async function reopenStageAction(
  slug: string,
  stageKey: string,
  feedback: string,
): Promise<ActionResult> {
  return changeCampaign(slug, () => reopenStage(slug, stageKey, feedback));
}

import "server-only";

import { auth } from "@clerk/nextjs/server";

import { EngineError } from "@/lib/engine-error";

/**
 * Server-side client for the we-OS engine.
 *
 * The BFF holds the session and forwards the Clerk token; the engine verifies
 * it independently and derives the tenant from the verified claim (ADR-0013).
 * The browser never calls the engine directly, and no request ever carries a
 * business identity — the tenant is not ours to send.
 */

const ENGINE_BASE_URL = process.env.ENGINE_BASE_URL ?? "http://127.0.0.1:8000";

/**
 * Calls the engine on behalf of the signed-in user.
 *
 * Args:
 *   path: The engine path, e.g. `/campaigns/spring/gate`.
 *   init: Optional fetch options; `Authorization` is always set here.
 *
 * Returns:
 *   The parsed JSON body.
 *
 * Throws:
 *   EngineError: When the engine answers with a non-2xx status.
 */
export async function engineFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const { getToken } = await auth();
  const token = await getToken();

  const response = await fetch(`${ENGINE_BASE_URL}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      ...init.headers,
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail =
      (body as { detail?: Record<string, unknown> }).detail ?? body;
    throw new EngineError(response.status, detail as Record<string, unknown>);
  }

  return (await response.json()) as T;
}

/**
 * Opens a streaming engine response on behalf of the signed-in user.
 *
 * The same adapter as `engineFetch`, for the one case a JSON round trip cannot
 * serve: Server-Sent Events, whose body must reach the browser unread. The
 * response is returned whole rather than parsed, so the caller can pipe it.
 *
 * Args:
 *   path: The engine path, e.g. `/runs/abc/stream`.
 *   signal: Aborts the upstream request when the reader goes away.
 *
 * Returns:
 *   The engine's raw response, successful or not.
 */
export async function engineStream(
  path: string,
  signal: AbortSignal,
): Promise<Response> {
  const { getToken } = await auth();
  const token = await getToken();

  return fetch(`${ENGINE_BASE_URL}${path}`, {
    cache: "no-store",
    signal,
    headers: {
      Accept: "text/event-stream",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
}

/**
 * Turns a failed engine call into the sentence a screen shows.
 *
 * The engine explains its own refusals in the operator's terms, so its message
 * is passed through; only an unreachable engine needs wording of ours, and that
 * wording should be the same on every screen.
 *
 * Args:
 *   error: The failure raised while calling the engine.
 *
 * Returns:
 *   The message to render.
 */
export { EngineError };

/**
 * Turns a failed engine call into the sentence a screen shows.
 *
 * The engine explains its own refusals in the operator's terms, so its message
 * is passed through; only an unreachable engine needs wording of ours, and that
 * wording should be the same on every screen.
 *
 * Args:
 *   error: The failure raised while calling the engine.
 *
 * Returns:
 *   The message to render.
 */
export function engineErrorMessage(error: unknown): string {
  if (error instanceof EngineError) return error.message;
  return "Could not reach the engine. Is it running on ENGINE_BASE_URL?";
}

export interface Me {
  user_id: string;
  email: string | null;
  business_name: string;
}

export interface GateReport {
  ok: boolean;
  issues: string[];
}

export interface DeliverableFile {
  name: string;
  path: string;
}

export interface DeliverableList {
  slug: string;
  files: DeliverableFile[];
}

/** Resolves the verified identity to the business its tenant represents. */
export function getMe(): Promise<Me> {
  return engineFetch<Me>("/me");
}

/**
 * Reports whether the tenant's Brand DNA and a campaign's goal are complete.
 *
 * Args:
 *   slug: The campaign slug.
 */
export function getGate(slug: string): Promise<GateReport> {
  return engineFetch<GateReport>(`/campaigns/${encodeURIComponent(slug)}/gate`);
}

/**
 * Lists the deliverables written for a campaign.
 *
 * Args:
 *   slug: The campaign slug.
 */
export function getDeliverables(slug: string): Promise<DeliverableList> {
  return engineFetch<DeliverableList>(
    `/campaigns/${encodeURIComponent(slug)}/deliverables`,
  );
}

export interface Deliverable extends DeliverableFile {
  content: string;
}

/**
 * Reads one deliverable's markdown content.
 *
 * Args:
 *   slug: The campaign slug.
 *   name: The deliverable filename, e.g. `research.md`.
 */
export function getDeliverable(
  slug: string,
  name: string,
): Promise<Deliverable> {
  return engineFetch<Deliverable>(
    `/campaigns/${encodeURIComponent(slug)}/deliverables/${encodeURIComponent(name)}`,
  );
}

export interface Question {
  id: string;
  field: string;
  section: string;
  text: string;
  why_we_ask: string;
  help_text: string;
  input_type: string;
  required: boolean;
  options: string[];
}

export interface Questionnaire {
  version: number;
  published_at: string;
  questions: Question[];
}

export interface DnaAnswer {
  question_id: string;
  answer: string;
}

export interface BrandDna {
  questionnaire_version: number;
  updated_at: string | null;
  markdown: string;
  answers: DnaAnswer[];
}

export interface MissingField {
  question_id: string;
  field: string;
  label: string;
}

export interface DnaCompleteness {
  complete: boolean;
  questionnaire_version: number;
  required_total: number;
  required_answered: number;
  missing: MissingField[];
  unanswered_new_questions: string[];
}

/** Reads the published question set the onboarding wizard renders from. */
export function getQuestionnaire(): Promise<Questionnaire> {
  return engineFetch<Questionnaire>("/questionnaire");
}

/** Reads the tenant's Brand DNA — the structured answers and their markdown projection. */
export function getBrandDna(): Promise<BrandDna> {
  return engineFetch<BrandDna>("/brand-dna");
}

/** Reports which Required Brand DNA fields the business still owes. */
export function getBrandDnaCompleteness(): Promise<DnaCompleteness> {
  return engineFetch<DnaCompleteness>("/brand-dna/completeness");
}

/**
 * Saves questionnaire answers, upserting so onboarding can be resumed.
 *
 * Args:
 *   answers: The answers to save; at least one.
 *
 * Returns:
 *   The updated completeness report.
 */
export function saveBrandDnaAnswers(
  answers: DnaAnswer[],
): Promise<DnaCompleteness> {
  return engineFetch<DnaCompleteness>("/brand-dna/answers", {
    method: "POST",
    body: JSON.stringify({ answers }),
  });
}

export interface Timeframe {
  start_date: string;
  end_date: string;
}

export interface Budget {
  amount: number;
  currency: string;
}

export interface KpiTiers {
  business: string;
  marketing: string;
  creative: string;
}

export interface CampaignGoalInput {
  name: string;
  objective: string;
  timeframe: Timeframe;
  budget: Budget;
  audience_segment: string;
  kpis: KpiTiers;
  offer?: string;
  constraints?: string;
}

export interface CampaignStage {
  key: string;
  phase: string;
  state: string;
  approval_policy: string;
  latest_version: number | null;
  stale: boolean;
}

export interface Campaign extends CampaignGoalInput {
  id: string;
  status: string;
  stages: CampaignStage[];
}

export interface StageProgress {
  completed: number;
  total: number;
  current_stage_key: string | null;
}

export interface CampaignSummary {
  id: string;
  name: string;
  objective: string;
  status: string;
  stage_progress: StageProgress;
  blocked_reason: string | null;
}

/**
 * Creates a campaign from its goal.
 *
 * Args:
 *   goal: The campaign goal the business filled in.
 *
 * Returns:
 *   The created campaign, in `draft`.
 */
export function createCampaign(goal: CampaignGoalInput): Promise<Campaign> {
  return engineFetch<Campaign>("/campaigns", {
    method: "POST",
    body: JSON.stringify(goal),
  });
}

/** Lists the tenant's active campaigns, archived ones excluded. */
export function listCampaigns(): Promise<{ campaigns: CampaignSummary[] }> {
  return engineFetch<{ campaigns: CampaignSummary[] }>("/campaigns");
}

/**
 * Reads one campaign: its goal, lifecycle status, and per-stage state.
 *
 * Args:
 *   slug: The campaign slug.
 */
export function getCampaign(slug: string): Promise<Campaign> {
  return engineFetch<Campaign>(`/campaigns/${encodeURIComponent(slug)}`);
}

/**
 * Archives a campaign, taking it off the active list.
 *
 * Args:
 *   slug: The campaign slug.
 */
export function archiveCampaign(slug: string): Promise<Campaign> {
  return engineFetch<Campaign>(
    `/campaigns/${encodeURIComponent(slug)}/archive`,
    { method: "POST" },
  );
}

/** Reads the audience segments a campaign may target, from the Brand DNA. */
export function getAudienceSegments(): Promise<{ segments: string[] }> {
  return engineFetch<{ segments: string[] }>("/brand-dna/segments");
}

export interface DeliverableSummary {
  stage_key: string;
  latest_version: number;
  stale: boolean;
  updated_at: string;
}

export interface StageDeliverable {
  name: string;
  path: string;
  stage_key: string;
  stale: boolean;
  content: string;
}

export interface DeliverableVersionSummary {
  stage_key: string;
  version: number;
  created_at: string;
  feedback: string | null;
  feedback_source: string | null;
  supersedes_version: number | null;
  sequence: number;
}

export interface DeliverableVersionDetail extends DeliverableVersionSummary {
  slug: string;
  content: string;
  latest: boolean;
}

export interface RunHandle {
  run_id: string;
  slug: string;
  stage: string | null;
  status: string;
}

export interface ActiveRun {
  run_id: string;
  slug: string;
  stage: string | null;
}

/**
 * Lists what a campaign has produced, with each deliverable's staleness.
 *
 * Args:
 *   slug: The campaign slug.
 */
export function getDeliverableSummaries(
  slug: string,
): Promise<{ slug: string; deliverables: DeliverableSummary[] }> {
  return engineFetch<{ slug: string; deliverables: DeliverableSummary[] }>(
    `/campaigns/${encodeURIComponent(slug)}/deliverables`,
  );
}

/**
 * Reads the latest version of one stage's deliverable.
 *
 * Args:
 *   slug: The campaign slug.
 *   name: The deliverable filename, e.g. `brand-strategy.md`.
 */
export function getStageDeliverable(
  slug: string,
  name: string,
): Promise<StageDeliverable> {
  return engineFetch<StageDeliverable>(
    `/campaigns/${encodeURIComponent(slug)}/deliverables/${encodeURIComponent(name)}`,
  );
}

/**
 * Lists a deliverable's versions, newest first, with the feedback behind each.
 *
 * Args:
 *   slug: The campaign slug.
 *   name: The deliverable filename.
 */
export function getDeliverableVersions(
  slug: string,
  name: string,
): Promise<{ stage_key: string; versions: DeliverableVersionSummary[] }> {
  return engineFetch<{
    stage_key: string;
    versions: DeliverableVersionSummary[];
  }>(
    `/campaigns/${encodeURIComponent(slug)}/deliverables/${encodeURIComponent(name)}/versions`,
  );
}

/**
 * Reads one historical version of a deliverable.
 *
 * Args:
 *   slug: The campaign slug.
 *   name: The deliverable filename.
 *   version: The version number to read.
 */
export function getDeliverableVersion(
  slug: string,
  name: string,
  version: number,
): Promise<DeliverableVersionDetail> {
  return engineFetch<DeliverableVersionDetail>(
    `/campaigns/${encodeURIComponent(slug)}/deliverables/${encodeURIComponent(name)}/versions/${version}`,
  );
}

/**
 * Starts a detached run of a campaign's pipeline.
 *
 * Args:
 *   slug: The campaign slug.
 *   stage: A single stage to run, or null for the whole pipeline.
 */
export function startRun(
  slug: string,
  stage: string | null = null,
): Promise<RunHandle> {
  return engineFetch<RunHandle>(`/campaigns/${encodeURIComponent(slug)}/run`, {
    method: "POST",
    body: JSON.stringify({ stage }),
  });
}

/** Lists the runs the caller currently has in flight. */
export function listActiveRuns(): Promise<{ runs: ActiveRun[] }> {
  return engineFetch<{ runs: ActiveRun[] }>("/runs");
}

/**
 * Reads a run's lifecycle status.
 *
 * Args:
 *   runId: The run id.
 */
export function getRun(runId: string): Promise<RunHandle> {
  return engineFetch<RunHandle>(`/runs/${encodeURIComponent(runId)}`);
}

/**
 * Approves the stage a run is halted at; the run resumes into the next stage.
 *
 * Args:
 *   runId: The halted run.
 *   stageKey: The stage being approved.
 */
export function approveStage(
  runId: string,
  stageKey: string,
): Promise<RunHandle> {
  return engineFetch<RunHandle>(`/runs/${encodeURIComponent(runId)}/approve`, {
    method: "POST",
    body: JSON.stringify({ stage_key: stageKey }),
  });
}

/**
 * Sends the waiting stage back with feedback, producing a new version.
 *
 * Args:
 *   runId: The halted run.
 *   stageKey: The stage being sent back.
 *   feedback: What the business owner wants changed.
 */
export function reviseStage(
  runId: string,
  stageKey: string,
  feedback: string,
): Promise<RunHandle> {
  return engineFetch<RunHandle>(`/runs/${encodeURIComponent(runId)}/revise`, {
    method: "POST",
    body: JSON.stringify({ stage_key: stageKey, feedback }),
  });
}

/**
 * Re-opens an approved stage, re-running it alone and marking downstream stale.
 *
 * Args:
 *   slug: The campaign slug.
 *   stageKey: The stage to re-open.
 *   feedback: What the owner wants changed, now they have changed their mind.
 */
export function reopenStage(
  slug: string,
  stageKey: string,
  feedback: string,
): Promise<RunHandle> {
  return engineFetch<RunHandle>(
    `/campaigns/${encodeURIComponent(slug)}/stages/${encodeURIComponent(stageKey)}/reopen`,
    { method: "POST", body: JSON.stringify({ feedback }) },
  );
}

export interface CampaignUsage {
  slug: string;
  used: number;
}

export interface UsageReport {
  used: number;
  allowance: number;
  remaining: number;
  exhausted: boolean;
  campaigns: CampaignUsage[];
}

/** Reports what the tenant has spent against their allowance, and where. */
export function getUsage(): Promise<UsageReport> {
  return engineFetch<UsageReport>("/usage");
}

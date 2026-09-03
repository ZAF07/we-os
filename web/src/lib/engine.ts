import "server-only";

import { auth } from "@clerk/nextjs/server";

/**
 * Server-side client for the we-OS engine.
 *
 * The BFF holds the session and forwards the Clerk token; the engine verifies
 * it independently and derives the tenant from the verified claim (ADR-0013).
 * The browser never calls the engine directly, and no request ever carries a
 * business identity — the tenant is not ours to send.
 */

const ENGINE_BASE_URL = process.env.ENGINE_BASE_URL ?? "http://127.0.0.1:8000";

/** A typed error mirroring the engine's `Error` schema from the frozen contract. */
export class EngineError extends Error {
  readonly status: number;
  readonly type: string;
  readonly detail: Record<string, unknown>;

  constructor(status: number, detail: Record<string, unknown>) {
    super(String(detail.message ?? `Engine request failed (${status})`));
    this.name = "EngineError";
    this.status = status;
    this.type = String(detail.type ?? "internal");
    this.detail = detail;
  }
}

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

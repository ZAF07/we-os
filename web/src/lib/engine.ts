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
export async function engineFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
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
    const detail = (body as { detail?: Record<string, unknown> }).detail ?? body;
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
  return engineFetch<DeliverableList>(`/campaigns/${encodeURIComponent(slug)}/deliverables`);
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
export function getDeliverable(slug: string, name: string): Promise<Deliverable> {
  return engineFetch<Deliverable>(
    `/campaigns/${encodeURIComponent(slug)}/deliverables/${encodeURIComponent(name)}`,
  );
}

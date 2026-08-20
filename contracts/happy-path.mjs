// Drives the operator happy path against the Prism mock server, proving the
// frontend can complete it with no engine present: sign in, see the DNA
// completeness report, create a campaign, start a run, hit an approval gate,
// approve, read a deliverable — plus the error shapes the contract freezes
// (unauthenticated, cross-tenant not_found, gate failure, quota exhaustion).
//
// Prism serves the spec's examples; named examples are selected with the
// `Prefer: example=<name>` header, and error shapes with `Prefer: code=<n>`.

import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const PORT = process.env.PRISM_PORT ?? "4013";
const BASE = `http://127.0.0.1:${PORT}`;
const AUTH = { Authorization: "Bearer test-token" };
const HERE = dirname(fileURLToPath(import.meta.url));

let failures = 0;

function check(label, condition, detail = "") {
  if (condition) {
    console.log(`  ok  ${label}`);
  } else {
    failures += 1;
    console.error(`FAIL  ${label}${detail ? ` — ${detail}` : ""}`);
  }
}

async function request(method, path, { headers = {}, body, raw = false } = {}) {
  const response = await fetch(`${BASE}${path}`, {
    method,
    headers: {
      ...AUTH,
      ...(body ? { "Content-Type": "application/json" } : {}),
      ...headers,
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const payload = raw ? await response.text() : await response.json().catch(() => null);
  return { status: response.status, payload };
}

async function waitForPrism(deadlineMs) {
  const start = Date.now();
  while (Date.now() - start < deadlineMs) {
    try {
      const response = await fetch(`${BASE}/health`);
      if (response.ok) return;
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 250));
    }
  }
  throw new Error(`Prism did not become ready on :${PORT}`);
}

async function main() {
  console.log("— sign in —");
  const me = await request("GET", "/me");
  check("GET /me returns the signed-in business", me.status === 200 && me.payload.business_name);
  check(
    "identity payload never carries a caller-suppliable tenant parameter",
    !("tenant_id" in (me.payload ?? {})) && !("customer" in (me.payload ?? {}))
  );

  console.log("— unauthenticated refusal shape —");
  const unauth = await request("GET", "/me", { headers: { Prefer: "code=401" } });
  check(
    "401 carries the typed unauthenticated error",
    unauth.status === 401 && unauth.payload?.type === "unauthenticated"
  );

  console.log("— questionnaire and DNA completeness —");
  const questionnaire = await request("GET", "/questionnaire");
  const firstQuestion = questionnaire.payload?.questions?.[0];
  check(
    "questionnaire carries text / why / help / input type / required",
    questionnaire.status === 200 &&
      firstQuestion &&
      ["text", "why_we_ask", "help_text", "input_type", "required"].every((k) => k in firstQuestion)
  );
  const completeness = await request("GET", "/brand-dna/completeness", {
    headers: { Prefer: "example=complete" },
  });
  check(
    "completeness report says the DNA is ready",
    completeness.status === 200 && completeness.payload.complete === true
  );
  const missing = await request("GET", "/brand-dna/completeness", {
    headers: { Prefer: "example=incomplete" },
  });
  check(
    "incomplete report names each missing Required field",
    missing.status === 200 && missing.payload.missing.every((m) => m.field && m.question_id)
  );

  console.log("— create a campaign —");
  const created = await request("POST", "/campaigns", {
    body: {
      name: "Spring refill push",
      objective: "120 refill subscriptions in 8 weeks",
      timeframe: { start_date: "2026-09-01", end_date: "2026-10-27" },
      budget: { amount: 4000, currency: "SGD" },
      audience_segment: "Weekday regulars",
      kpis: {
        business: "120 refill subscriptions",
        marketing: "2.5% landing-page conversion",
        creative: "30% hook rate on launch video",
      },
    },
  });
  check("POST /campaigns creates a draft campaign", created.status === 201 && created.payload.id);
  const stages = created.payload?.stages ?? [];
  check(
    "stages arrive in the mandatory order with performance-plan before creative-brief",
    JSON.stringify(stages.map((s) => s.key)) ===
      JSON.stringify([
        "research",
        "brand-strategy",
        "campaign-strategy",
        "performance-plan",
        "creative-brief",
        "asset-prompts",
      ])
  );
  check(
    "every stage reports its operator Phase and approval policy",
    stages.every((s) => s.phase && s.approval_policy)
  );
  check(
    "lifecycle status is a separate field from stage progress",
    created.payload.status === "draft"
  );
  const campaignId = created.payload.id;

  console.log("— start a run and hit the approval gate —");
  const run = await request("POST", `/campaigns/${campaignId}/runs`);
  check("POST /runs starts a run (202)", run.status === 202 && run.payload.run_id);
  const runId = run.payload.run_id;
  const awaiting = await request("GET", `/runs/${runId}`, {
    headers: { Prefer: "example=awaiting-approval" },
  });
  check(
    "run halts awaiting approval at brand-strategy",
    awaiting.status === 200 &&
      awaiting.payload.status === "awaiting_approval" &&
      awaiting.payload.awaiting_approval_stage_key === "brand-strategy"
  );

  console.log("— approve and continue —");
  const approved = await request("POST", `/runs/${runId}/approve`, {
    body: { stage_key: "brand-strategy" },
  });
  check(
    "approve resumes the run",
    approved.status === 200 && approved.payload.status === "running"
  );

  console.log("— read the deliverable —");
  const deliverable = await request("GET", `/campaigns/${campaignId}/deliverables/brand-strategy`);
  check(
    "deliverable exposes content, version, supersession, staleness",
    deliverable.status === 200 &&
      deliverable.payload.content.includes("# Brand Strategy") &&
      typeof deliverable.payload.version === "number" &&
      "supersedes_version" in deliverable.payload &&
      typeof deliverable.payload.stale === "boolean"
  );
  const versions = await request(
    "GET",
    `/campaigns/${campaignId}/deliverables/brand-strategy/versions`
  );
  check(
    "version history records the feedback that produced each version",
    versions.status === 200 && versions.payload.versions.some((v) => v.feedback)
  );

  console.log("— revise with feedback —");
  const revised = await request("POST", `/runs/${runId}/revise`, {
    body: { stage_key: "brand-strategy", feedback: "Anchor the positioning to convenience." },
  });
  check("revise is accepted (202)", revised.status === 202);

  console.log("— frozen error shapes —");
  const crossTenant = await request("GET", "/campaigns/cmp_spring", {
    headers: { Prefer: "code=404" },
  });
  check(
    "cross-tenant refusal is an indistinguishable not_found",
    crossTenant.status === 404 && crossTenant.payload?.type === "not_found"
  );
  const gateFailed = await request("POST", `/campaigns/${campaignId}/runs`, {
    headers: { Prefer: "code=409, example=gate-failed" },
  });
  check(
    "gate failure names every missing Required field",
    gateFailed.status === 409 &&
      gateFailed.payload?.type === "gate_failed" &&
      gateFailed.payload.missing_fields.length > 0
  );
  const conflict = await request("POST", `/campaigns/${campaignId}/runs`, {
    headers: { Prefer: "code=409, example=run-conflict" },
  });
  check(
    "run conflict carries the active run id",
    conflict.status === 409 && conflict.payload?.active_run_id
  );
  const quota = await request("POST", `/campaigns/${campaignId}/runs`, {
    headers: { Prefer: "code=402" },
  });
  check(
    "quota exhaustion is a typed 402",
    quota.status === 402 && quota.payload?.type === "quota_exhausted"
  );

  console.log("— cancel —");
  const cancelled = await request("POST", `/runs/${runId}/cancel`);
  check(
    "cancel reports the cancelled run",
    cancelled.status === 200 && cancelled.payload.status === "cancelled"
  );
}

const prism = spawn(
  process.execPath,
  [join(HERE, "node_modules", ".bin", "prism"), "mock", join(HERE, "openapi.yaml"), "--port", PORT],
  { stdio: ["ignore", "pipe", "pipe"] }
);
prism.stderr.on("data", (chunk) => process.env.PRISM_DEBUG && process.stderr.write(chunk));

try {
  await waitForPrism(30_000);
  await main();
} finally {
  prism.kill("SIGTERM");
}

if (failures > 0) {
  console.error(`\n${failures} happy-path check(s) failed`);
  process.exit(1);
}
console.log("\nHappy path complete against the mock server — no engine present.");

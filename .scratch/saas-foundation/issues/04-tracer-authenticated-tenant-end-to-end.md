# 04 — Tracer bullet: one authenticated tenant, end to end

Status: ready-for-agent
Type: task

## Parent

[PRD: we-OS SaaS foundation](../PRD.md) · [ADR-0013](../../../docs/adr/0013-multi-tenant-saas-with-dual-verified-jwt.md) · [ADR-0022](../../../docs/adr/0022-brand-dna-and-the-overloaded-customer.md)

## What to build

The thinnest complete path through every layer, proving the architecture before the expensive slices commit to it. A real person logs in and drives a real campaign end to end.

The path: sign in against the managed IdP → the frontend verifies the token and forwards it → the engine verifies it **independently** and derives the tenant from the verified claim → the tenant's Brand DNA is read through the `DocumentStore` → the DNA Gate reports completeness → a run starts → a deliverable is read back and rendered in the browser.

Two structural changes land with it:

- **The `customer` parameter is removed**, not validated. A tenant is one business ([ADR-0022](../../../docs/adr/0022-brand-dna-and-the-overloaded-customer.md)), so a caller-supplied business identity is fully redundant with the verified claim — and accepting one is exactly what ADR-0013 forbids. This covers the operation bodies, the query parameters, the CLI argument, and the graph state key.
- **Tenant scoping is enforced inside the `DocumentStore`**, not at call sites, so new code cannot forget it.

Storage stays on the filesystem adapter — Postgres is slice 05. The point of this slice is to prove identity, tenancy and the full round trip, not persistence.

The frontend contribution is deliberately thin: a real sign-in, and one screen showing the tenant's DNA completeness and a deliverable. The designed screens are wired in slices 10–12.

## Acceptance criteria

- [ ] A user signs in through the IdP and reaches an authenticated screen.
- [ ] The engine verifies the token itself and rejects a request with no token, an expired token, and a token with an invalid signature.
- [ ] A request carrying a valid identity for a different tenant is refused for every resource type — Brand DNA, campaign, run, deliverable.
- [ ] No operation, CLI argument, or graph state key accepts a business identity from the caller.
- [ ] Tenant scoping is enforced in the storage layer; a test proves a repository call without an explicit scope cannot return another tenant's document.
- [ ] The DNA Gate refuses a run when Required fields are missing and names every missing field.
- [ ] A run started from the browser completes, and its deliverable is fetched and rendered.
- [ ] The auth dependency is overridable in tests to inject a verified claim; no test contacts a live IdP.
- [ ] `uv run pytest`, `uv run ruff check .`, `uv run ruff format`, `uv run mypy src` all pass.
- [ ] Verified in the running app, not only in tests.

## Blocked by

- [02 — Introduce the DocumentStore port](02-introduce-documentstore-port.md)
- [03 — Freeze the API contract and stand up a mock server](03-freeze-api-contract-and-mock-server.md)

## Comments

**2026-08-30 — engine complete and verified; frontend awaiting Clerk keys.**

Decisions taken (both by the operator):

- **IdP is Clerk.** The engine stays vendor-neutral: a `TokenVerifier` port
  (`ports.py`) with an OIDC/JWKS adapter (`adapters/auth.py`) using PyJWT. The
  engine holds **no Clerk secret** — only the public issuer URL, since JWKS is
  public. Swapping IdP is a config change.
- **`tenant_id` is the Clerk Organization `org_id`**, not the user `sub`. A token
  with no `org_id` is refused rather than falling back to the user id, which
  would weld a business to a single login and make tenancy unmigratable — and
  `tenant_id` becomes the Postgres RLS key in slice 05.

Structural changes beyond the literal ask, each forced by "cross-tenant refused
for **every** resource type":

- **Storage layout moved** from `customers/<name>/` + a shared `campaigns/` tree
  to `tenants/<tenant>/{dna.md,campaigns/<slug>/}`. Campaign documents were
  previously shared across all tenants by the filesystem adapter. Existing
  `coast-coffee` data was migrated in place.
- **Run traces moved** to `logs/<tenant>/<slug>/`, so a run id is unfindable
  outside its tenant.
- **The read sandbox now refuses the whole `tenants/` subtree.** Specialists
  previously could read any path under the repo root, so a subverted prompt could
  have read another business's Brand DNA. Tenant documents now reach agents only
  through the tenant-scoped `DocumentStore`; `dna_path` in the stage brief is the
  logical `dna.md`, so no tenant id is ever visible to a model.
- **Error bodies now match the frozen contract** (`{type, status, message}` at the
  top level, not nested under FastAPI's `detail`), and `Error.type` values are the
  contract's names (`gate_failed`, `run_conflict`, `not_found`, `unauthenticated`).
- **`templates/campaign-goal.md` lost its `**Customer:**` Required field** — it was
  a caller-supplied business identity inside the gated goal document.

Verified in the running app against a local RS256 JWKS issuer standing in for
Clerk (real signatures, real key fetch, no vendor account):

- Unauthenticated request to every route → 401 `unauthenticated`; `/health` → 200.
- Garbage/expired/foreign-signature/`alg:none` token → 401, never 500.
- No issuer configured + a token present → 500, i.e. it fails closed.
- `/me` derives `Coast Coffee` and `Rival Roasters` from their own `org_id`.
- Coast reads its real DNA (gate ok), lists 6 deliverables, reads `research.md`
  (21,817 chars). Rival gets an identical 404 for the same slug, the same run id,
  the same trace, and the same deliverable — indistinguishable from absence.
- Stage 0 gate on a placeholder DNA → 409 `gate_failed` naming all 11 missing
  fields, and no run started.
- CLI: no tenant argument exists; tenant comes from `MARKETING_OS_TENANT_ID`, and
  its absence is a clear `ConfigError`.

Gates: 252 passed, 1 skipped; `ruff check`, `ruff format`, `mypy src` clean.
Frontend `tsc`, `eslint`, `next build` clean.

### Not done — needs the operator's Clerk keys

- **AC 1** (a user signs in and reaches an authenticated screen) and **AC 10**
  (verified in the running app) are unverified for the browser half. Everything is
  wired — `clerkMiddleware`, `/sign-in`, `/sign-up`, `ClerkProvider`, a
  server-only BFF client that forwards the token — but no Clerk account exists yet.
  Placeholders are in `web/.env.local.example` and `agent-harness/example.env`.
- **The Playwright suite cannot run** until those keys exist: every route is now
  behind auth. `@clerk/testing` is wired via `tests/auth.setup.ts` + a `setup`
  project, so `pnpm test` works once `E2E_CLERK_USER_EMAIL` / `_PASSWORD` are set.
- **`tenants/coast-coffee/` is keyed by slug, not an `org_...` id.** Rename that
  directory to the real Organization id once Clerk is provisioned, or the migrated
  data is unreachable by a real token.
- **AC 7** is partial: the workspace renders the DNA completeness report and reads
  a deliverable's content back, but there is no start-a-run control — run-launching
  UI is slice 11's scope.
- **AC 3** proves cross-tenant refusal for campaign, deliverable, run and gate. The
  Brand DNA is proven at the store layer only; there is no `/brand-dna` route yet
  (slice 06).
- `gate_failed.missing_fields` are prose strings; the contract wants `MissingField`
  objects with `question_id`. Deferred to slice 06, which introduces the
  questionnaire those ids come from.

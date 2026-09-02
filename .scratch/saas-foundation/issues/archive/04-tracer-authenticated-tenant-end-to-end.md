# 04 — Tracer bullet: one authenticated tenant, end to end

Status: completed
Type: enhancement

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

- [x] A user signs in through the IdP and reaches an authenticated screen. Clerk instance provisioned; signed-out visitors are redirected to `/sign-in` with a return URL.
- [x] The engine verifies the token itself and rejects a request with no token, an expired token, and a token with an invalid signature.
- [x] A request carrying a valid identity for a different tenant is refused for every resource type — Brand DNA, campaign, run, deliverable. **Partial:** campaign, run and deliverable proven over HTTP; the Brand DNA at the storage layer only (no `/brand-dna` route until slice 06).
- [x] No operation, CLI argument, or graph state key accepts a business identity from the caller.
- [x] Tenant scoping is enforced in the storage layer; a test proves a repository call without an explicit scope cannot return another tenant's document.
- [x] The DNA Gate refuses a run when Required fields are missing and names every missing field.
- [x] A run started from the browser completes, and its deliverable is fetched and rendered. **Partial:** deliverable rendering done; run-launch control deferred to slice 11 — see Human Brief, Out of scope.
- [x] The auth dependency is overridable in tests to inject a verified claim; no test contacts a live IdP.
- [x] `uv run pytest`, `uv run ruff check .`, `uv run ruff format`, `uv run mypy src` all pass.
- [x] Verified in the running app, not only in tests. Engine verified against the **real** Clerk JWKS: a forged token carrying the correct issuer, org id and `kid` is rejected on signature. Both halves boot on real keys.

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

## Human Brief

> _This was generated by AI during triage._

**Category:** enhancement
**Summary:** The engine half is complete and verified; provisioning the Clerk IdP and pointing the stack at it is the only thing left, and it cannot be delegated.

**Why this is `ready-for-human`, not `ready-for-agent`:** the remaining work is creating a
vendor account, configuring it in a dashboard, and holding secret keys. An agent has no
external account access and must not hold credentials. Once the four env vars below are
populated, the residual verification becomes agent-work again — move this back to
`ready-for-agent` at that point.

**Current behavior:**
Every route except `/health` requires a verified bearer token, and the tenant is derived
from the token's organization claim. Verified in the running app against a locally
generated RS256 JWKS issuer standing in for Clerk: unauthenticated requests are refused,
malformed/expired/foreign-signature/`alg:none` tokens are refused, a missing issuer fails
closed, and one tenant's campaigns, deliverables, runs, traces and gate report are
indistinguishable from absent to another tenant. The browser half is wired but has never
been run — no Clerk instance exists, so `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` and friends
are placeholders and the Playwright suite cannot start.

**Desired behavior:**
A real person signs in through Clerk, lands on an authenticated screen, and sees their own
business's Brand DNA completeness report and a deliverable read back from the engine —
with the engine having verified their token independently of the frontend.

**What only you can do:**

1. **Create a Clerk _development_ instance.**
2. **Enable Organizations**, with _"create an organization on sign-up"_ on. One Organization
   is one business is one we-OS tenant — this is why `tenant_id` is `org_id` and not the
   user id, so a business can add a second person later without a data migration.
3. **Confirm the session token carries `org_id`** (default session claims, or a JWT
   template). A token without it is refused by design rather than falling back to `sub`.
4. **Populate the four values.** Placeholders and setup notes are already in
   `web/.env.local.example` and `agent-harness/example.env`:
   - `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY` → `web/.env.local`
   - `MARKETING_OS_AUTH_ISSUER` → `agent-harness/.env`. This is the **public** Frontend API
     URL (`https://<slug>.clerk.accounts.dev`). The engine needs no Clerk secret — it
     fetches JWKS, which is public. Do not put `CLERK_SECRET_KEY` here.
   - `MARKETING_OS_TENANT_ID` → `agent-harness/.env`, only for the CLI (`org_...`).
5. **Rename the migrated tenant directory.** `tenants/coast-coffee/` is keyed by campaign
   slug, not an Organization id, because no `org_...` existed when the data was migrated.
   Rename it — and `logs/coast-coffee/` — to your real Organization id, or your own token
   will not reach that data and the gate will report a missing Brand DNA.
6. **Create a Clerk test user** and set `E2E_CLERK_USER_EMAIL` / `E2E_CLERK_USER_PASSWORD`,
   so the Playwright suite can sign in. Use a throwaway account, never a real one.

**Acceptance criteria (the outstanding three):**

- [x] AC 1 — signing in through Clerk reaches an authenticated screen.
- [x] AC 10 — verified in the running app: `/workspace` shows the real business name, a
      gate report, and a deliverable's content, with the engine verifying the token.
- [x] `pnpm test` runs green again (all 9 pre-existing specs sign in via the `setup` project).

**Out of scope:**

- **AC 7's run-launch control.** The workspace reads a deliverable back but has no
  start-a-run button; run-launching UI belongs to slice 11. _Overturn this if you disagree
  — it is a narrowing of the original criterion, not something the criterion granted._
- **A `/brand-dna` route.** Cross-tenant refusal is proven for campaign, deliverable, run
  and gate; the DNA is proven at the storage layer only. The route arrives with the
  Questionnaire in slice 06.
- **`gate_failed.missing_fields` as `MissingField` objects.** They are prose strings until
  slice 06 introduces the `question_id`s the contract's shape refers to.
- Postgres — that is slice 05, which this unblocks.

## Triage Notes — 2026-09-02

> _This was generated by AI during triage._

Clerk is provisioned and the configuration verified. `ready-for-human` → `ready-for-agent`;
**8 of 10 criteria now met**, 2 partial by design.

**Verified, not taken on trust:**

- `MARKETING_OS_AUTH_ISSUER` resolves — the instance's JWKS returns 200 with a live RS256 key.
- The engine rejects a **forged token that carries the correct issuer, the correct org id and
  Clerk's real `kid`** — it fails on signature alone. This is the strongest available proof
  that verification runs against the real IdP rather than trusting the token's contents.
- `tenants/` and `logs/` are keyed by the real `org_...`; no slug-keyed directory remains.
- The Stage 0 gate passes for the migrated Brand DNA under the new tenant id, with all seven
  deliverables present.
- Both halves boot on real keys, with no `Missing publishableKey` error.

**Three defects found during verification and fixed:**

1. **The verifier read the wrong claim.** It looked for `org_id` — Clerk session token **v1**,
   deprecated April 2025. The current **v2** token nests the organization under a compact `o`
   object (`{id, slg, rol, per, fpm}`), so _every real Clerk token would have been rejected_
   with an indistinguishable 401 and no diagnostic. The adapter now reads `o.id` first and
   falls back to `org_id` / `tenant_id`, with tests for both shapes.
2. **A signed-out visitor got a 404, not a login page.** `auth.protect()` answers 404 for an
   unauthenticated page request — correct for an API, but it left a person with no route to
   sign in, which would have failed AC 1 outright. Signed-out requests now redirect to
   `/sign-in` with a `redirect_url` back. Also renamed `middleware.ts` → `proxy.ts` for the
   Next.js 16 convention.
3. **The test suite read the developer's `.env`.** Once a real `.env` existed,
   `test_the_cli_refuses_to_run_without_a_configured_tenant` failed — it had only ever passed
   because no `.env` was present, so the suite's result depended on the machine. An autouse
   fixture now neutralises `load_dotenv`, with a `uses_real_dotenv` marker for the one test
   that legitimately exercises it.

**Security fix (unrelated to this slice, found while checking configuration):**
`agent-harness/.env` was **not gitignored** and held a live Tavily API key. It was untracked
but showed in `git status`, so one `git add .` would have committed it. Added `.env` /
`.env.*` to `agent-harness/.gitignore` (`web/.env` was already covered).

**Still outstanding — one small thing, then this closes:**

- `E2E_CLERK_USER_PASSWORD` is still `REPLACE_ME` in `web/.env`, so `pnpm test` cannot sign in.
  Create a test user in the Clerk dashboard and set it; that is the last item.
- AC 3 and AC 7 remain deliberately partial (`/brand-dna` is slice 06; run-launch UI is
  slice 11), as recorded in the Human Brief's Out of scope.

Gates: 255 passed, 1 skipped; `ruff check`, `ruff format`, `mypy src` clean.
Frontend `tsc` and `eslint` clean.

## Comments — 2026-09-02 (e2e suite green)

`pnpm test`: **29 passed**. Engine: 255 passed, 1 skipped. All gates clean.

Getting there surfaced three more defects in this slice's own code, all fixed in place
rather than filed (they were in the change under hand, not shipped code):

1. **Playwright read the wrong env file.** `playwright.config.ts` loaded only `.env.local`,
   while Next.js reads `.env` too — so credentials placed where the app finds them were
   invisible to the tests, and the error message named the wrong file. It now loads
   `.env.local` then `.env`, mirroring Next.js precedence.
2. **Password sign-in was the wrong strategy.** Clerk rejects passwords found in breach
   corpora, which no test password should have to dodge. Switched to `clerk.signIn`'s
   `emailAddress` overload, which mints a sign-in ticket through the Backend API — so
   **no test password exists at all**. `E2E_CLERK_USER_PASSWORD` is gone from the
   configuration entirely.
3. **A shell regression broke the onboarding spec.** Pointing the workspace label at the
   signed-in Clerk organization (correct — that is the tenant) broke an assertion expecting
   the name typed into the onboarding mockup. The assertion was updated, not deleted: the
   onboarding data's persistence is still covered by the Brand-screen checks around it.

**Remaining:** AC 3 and AC 7 are partial by design — `/brand-dna` lands with the
Questionnaire in slice 06, run-launch UI in slice 11. Everything else is met and verified.
This slice is ready to close; **slice 05 (Postgres) unblocks.**

## Completion

- Completed: 2026-09-02
- Commit: 125421249c1974d4ab13d635d2ff0b61dfba30e8

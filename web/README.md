# we-OS — operator interface

The Next.js app and its BFF (ADR-0012). The browser never calls the engine
directly: this app holds the Clerk session, forwards the verified token, and the
engine derives the tenant from that claim (ADR-0013).

## Running it locally

You need the engine running as well — the app renders nothing of its own.

```bash
# terminal 1 — the engine
cd agent-harness && make start

# terminal 2 — this app
cd web && pnpm install && pnpm dev
```

Both read configuration from local env files, neither of which is committed:

| File                 | Copy from                   | Holds                                            |
| -------------------- | --------------------------- | ------------------------------------------------ |
| `web/.env.local`     | `web/.env.local.example`    | Clerk keys, `ENGINE_BASE_URL`, the e2e values    |
| `agent-harness/.env` | `agent-harness/example.env` | the LLM provider key, `MARKETING_OS_AUTH_ISSUER` |

## Tests

Two suites, and they answer different questions.

**Unit tests** cover the pure logic the screens are built on — the projections
between engine vocabulary and operator vocabulary. They need nothing: no
credentials, no server, no database.

```bash
pnpm test:unit
```

**The end-to-end suite** drives a real browser against the real app and the real
engine. It needs Clerk credentials and a seeded tenant, so it runs through a
Docker Compose stack that brings up everything together:

```bash
make test-e2e          # from the repository root
```

That builds and starts Postgres, the engine and this app, seeds the test
tenant's Brand DNA, runs the suite, and tears the stack down — passing or
failing. To keep the stack up between runs:

```bash
make e2e-up
cd web && E2E_STACK=compose pnpm test
make e2e-down
```

`E2E_STACK=compose` tells Playwright the app is already being served, so it
attaches instead of starting a second one on the same port.

### Getting the test credentials

The suite authenticates against the **shared team Clerk test instance**, not
your own dev instance. Ask a maintainer for access, then from the Clerk
dashboard fill these into `web/.env.local`:

| Variable                            | Where it comes from                                   |
| ----------------------------------- | ----------------------------------------------------- |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | API keys                                              |
| `CLERK_SECRET_KEY`                  | API keys — server-only, never prefixed `NEXT_PUBLIC_` |
| `MARKETING_OS_AUTH_ISSUER`          | the instance's Frontend API URL                       |
| `E2E_CLERK_USER_EMAIL`              | the seeded test user's email                          |
| `E2E_CLERK_ORG_ID`                  | Organizations — the org that user belongs to          |
| `E2E_CLERK_BLANK_USER_EMAIL`        | the blank test user's email                           |
| `E2E_CLERK_BLANK_ORG_ID`            | Organizations — a _second_ org, for the blank tenant  |

No test password is stored: sign-in mints a ticket through Clerk's Backend API
using `CLERK_SECRET_KEY`.

The organization ids are the ones that need explaining. A tenant id is minted
randomly (`ten_<uuid4>`) on a business's first authenticated request, so it
cannot be known in advance and a seed cannot simply write "the test tenant's"
Brand DNA. Instead `agent-harness/scripts/seed_test_tenants.py` writes the
`tenants` rows itself, pairing a fixed tenant id with each organization — so when
a test user signs in, the engine finds that row rather than minting a new one,
and the seeded state is already theirs.

There are two users because there are two tenants, and the engine derives the
tenant from the organization claim on the session token — so a second tenant
means a second organization, and a second dedicated user keeps that claim a
fixed property of a saved storage state rather than something a fixture has to
switch mid-run.

### What the seed guarantees

**The seeded tenant** — `Summit Climbing Collective`, with every Required Brand
DNA field answered so the DNA Gate passes, and two Audience Segments a spec can
name:

- `Urban 22-35 beginners curious about climbing`
- `Weekend boulderers plateauing at V4`

Assert on those rather than on "whatever the first radio happens to be".

Its **campaigns are purged** on every stack start. Specs create campaigns and
leave them behind, so without the purge the list grows on every `make test-e2e`
and a spec asserting on a campaign name matches two rows the second time it
runs. Everything a campaign owns goes with it: its documents, runs, deliverable
versions, usage rows and checkpoint threads. Mint any text a spec asserts on
with `uniqueName` from `tests/fixtures.ts` — ESLint refuses an inline
`Date.now()` in `tests/`, so that convention is enforced rather than remembered.

**The blank tenant** — `Blank Slate Testing`, with no Brand DNA at all: no
`dna_answers` rows and no `dna.md`. The onboarding specs run against it in their
own Playwright project (`chromium-onboarding`, one worker), because a complete
Brand DNA pre-fills the wizard and leaves its required-field gating nothing to
refuse. The last of those specs completes the wizard and fills the tenant in, so
blankness is re-established by the seed on every stack start — which means
re-running `pnpm test` against a stack that is already up fails that project.
Bring the stack up again (`make e2e-up`) first; the spec says so when it fails.

### CI

CI does not run the end-to-end suite — it needs Clerk secrets and a live engine.
The frontend's data contract is covered instead by
`agent-harness/tests/test_workspace_contract.py`, which runs in CI with no
credentials and fails if the engine stops returning a field the screens render.
See `.scratch/saas-foundation/issues/13-frontend-suite-cannot-run-without-credentials.md`.

## Quality gates

```bash
pnpm typecheck && pnpm lint && pnpm format:check && pnpm test:unit
```

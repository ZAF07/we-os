# we-OS — operator interface

The Next.js app and its BFF (ADR-0012). The browser never calls the engine
directly: this app holds the Clerk session, forwards the verified token, and the
engine derives the tenant from that claim (ADR-0013).

## Running it locally

You need the engine running as well for the signed-in half — Home and
everything behind it render nothing of their own. The public half (the Landing
at `/`, `/pricing`, `/get-started`, sign-in and sign-up) needs no engine.
Welcome (`/welcome`), where a new person names their business, sits between the
two: it needs a session but no engine until the moment it records the tier.

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
| `E2E_CLERK_TENANTLESS_USER_EMAIL`   | a _third_ test user, member of no organization at all |

No test password is stored: sign-in mints a ticket through Clerk's Backend API
using `CLERK_SECRET_KEY`.

The organization ids are the ones that need explaining. A tenant id is minted
randomly (`ten_<uuid4>`) on a business's first authenticated request, so it
cannot be known in advance and a seed cannot simply write "the test tenant's"
Brand DNA. Instead `agent-harness/scripts/seed_test_tenants.py` writes the
`tenants` rows itself, pairing a fixed tenant id with each organization — so when
a test user signs in, the engine finds that row rather than minting a new one,
and the seeded state is already theirs.

There are two users with organizations because there are two tenants, and the
engine derives the tenant from the organization claim on the session token — so
a second tenant means a second organization, and a second dedicated user keeps
that claim a fixed property of a saved storage state rather than something a
fixture has to switch mid-run. The third user has no organization for the
opposite reason: it is the person who has just signed up (see
[The tenantless session](#the-tenantless-session)).

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

### The visitor

The `chromium-public` project runs `tests/public.spec.ts` with no saved session
and no dependency on the sign-in setup, because the public half must work with
neither: a change that puts the Landing behind auth fails there rather than
passing on a signed-in cookie. It needs no engine either, so on its own it runs
without the stack — `pnpm test --project=chromium-public` starts the dev server
itself when the compose stack is not up.

### The tenantless session

A new sign-up lands authenticated with no organization — a **tenantless
session** — because We-OS creates the business itself, on Welcome, after a tier
has been chosen (ADR-0027). The `chromium-tenantless` project runs
`tests/tenantless.spec.ts` as that person, with its own sign-in
(`tests/tenantless.setup.ts`) and its own Clerk user, and proves two things:
that such a session cannot reach Home, Campaigns or anything else in the app
half, and that naming a business at Welcome creates it, records the tier, and
lands on Home.

The user stops being tenantless the moment a spec succeeds, so every spec
deletes the Organization it created through Clerk's Backend API afterwards, and
the setup deletes any a failed run left behind. It runs with one worker, like
the onboarding project, because its specs share that mutable fixture. It needs
the engine — recording the tier is an engine call — so it runs inside the
compose stack.

Two things about the Clerk instance make this work, and both live in the
dashboard rather than the repository. The tenantless user must exist and belong
to no organization. And the instance's Organizations settings must be set to
**Membership optional** (Personal Accounts on). The default, **Membership
required**, makes Clerk prompt every new session to create or join an
organization before it can reach the app: the session sits in a "pending"
state on a "choose-organization" task, the welcome flow never runs, and the
setup fails naming that task and this setting rather than passing on a session
that was never tenantless.

Until `E2E_CLERK_TENANTLESS_USER_EMAIL` is set, the project is **skipped** and
Playwright reports it so. That is deliberate: the user is provisioned by hand,
and a suite that stayed red for everyone until then would gate unrelated work
on it. Once the variable is set, anything wrong with the user or the instance
fails loudly.

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

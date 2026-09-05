# 15 — Two onboarding specs are permanently skipped, so the wizard's gating is untested

Status: completed
Type: task

## Parent

[PRD: we-OS SaaS foundation](../PRD.md) · follows [13 — the e2e stack](13-frontend-suite-cannot-run-without-credentials.md)

## Symptom

Two specs in `web/tests/onboarding.spec.ts` are `test.skip`ped and cannot be
un-skipped as the suite is built:

1. **`required-field validation blocks advancing past an incomplete step`** —
   asserts that pressing *Next →* on an incomplete step is refused and the
   wizard stays put.
2. **`completing the questionnaire lands on the Brand screen with the answers`**
   — walks the whole wizard and checks the answers arrive on Brand.

Neither is failing for a defect in the wizard. They are skipped because the e2e
stack **deliberately seeds a complete Brand DNA**
([13](13-frontend-suite-cannot-run-without-credentials.md)), and both
specs need a tenant with **none**:

- The first has nothing incomplete left to block on. The wizard correctly
  resumes on the first unanswered step, and for the seeded tenant there is no
  such step, so the refusal it asserts can never fire.
- The second rewrites the whole Brand DNA to a different business ("Acme
  Coffee"). The suite runs `fullyParallel` against one shared tenant, so doing
  that mid-run changes the Audience Segments every campaign spec is picking from
  at that moment.

The seed is not the problem — it is load-bearing. Every other spec needs a
tenant that *can* create campaigns, which means a DNA that passes the Stage 0
gate. The two requirements are genuinely in tension, and the current resolution
is to skip.

**Impact.** Required-field gating in onboarding — the thing that stops a
business reaching the pipeline with an incomplete Brand DNA — has no browser
coverage. That gate is the frontend half of a constraint the whole product rests
on (`.claude/rules/brand-dna.md`). A regression in it would ship silently.

## Repro

Deterministic — it is a skip, not a flake.

```bash
make test-e2e                     # 40 passed, 0 failed, 2 skipped
grep -n "test.skip" web/tests/onboarding.spec.ts
```

Removing either `.skip` and re-running reproduces the underlying conflict: the
first spec fails because the wizard opens past step 1 with answers already in
place; the second passes in isolation but destabilises campaign specs running
beside it.

## What's needed

**Decided** in the 2026-09-05 grilling session. Six decisions, in dependency
order; the reasoning for each is under Comments.

1. **A second Clerk test user, in a second Clerk organization.** The engine
   derives the tenant from the `org_id` claim on the session token
   (`PostgresTenantDirectory.resolve`), so the organization is the axis. A
   second dedicated user keeps that claim a fixed property of a saved storage
   state rather than something a fixture has to switch and re-verify.
2. **Seed the blank tenant explicitly**, with a fixed `BLANK_TENANT_ID`, rather
   than letting `resolve()` auto-provision it on first sign-in. Auto-provisioning
   does produce a blank tenant, but with a random id that nothing can name.
3. **One seed invocation writes both tenants.** No `--tenant-id`/`--blank`
   arguments and no second compose call: the two tenants are a matched pair and
   a half-seeded stack should be unrepresentable.
4. **The two onboarding specs run serially, in their own Playwright project**,
   against the blank tenant's storage state. Blankness is re-established by the
   seed on every stack start, not by the specs themselves.
5. **The blank tenant is seeded under a name the wizard then overwrites.** Spec 2
   answers `q_business_name` as "Acme Coffee" and asserts Brand shows it, which
   proves the answer won over the organization name (`render.py`) — an
   uncovered rule today.
6. **The campaign-accumulation problem gets its own issue**, not folded in here.

### Concretely

- `agent-harness/scripts/seed_test_tenant.py` — add `BLANK_TENANT_ID` and
  `BLANK_BUSINESS_NAME` constants and a `seed_blank(dsn, organization_id)` that
  writes the `tenants` row and **deletes** any `dna_answers` rows and the
  `dna.md` document for it. The delete is the point: blankness must be
  re-established on every start. `main()` calls both; rename the module to
  `seed_test_tenants.py` since it is no longer singular.
- `docker-compose.e2e.yml` — a second organization id env var
  (`E2E_CLERK_BLANK_ORG_ID`), passed to the same single invocation.
- `web/tests/auth.setup.ts` — loop over two `{email, storageState}` pairs,
  writing `.auth/user.json` and `.auth/blank-user.json`. Keep the route warm-up
  for the seeded session; the blank session needs only `/onboarding`.
- `web/playwright.config.ts` — a second project (`chromium-onboarding`) with
  `workers: 1`, the blank storage state, and `testMatch` for
  `onboarding.spec.ts`; the existing `chromium` project gains a matching
  `testIgnore` so the file runs once, not twice.
- `web/tests/onboarding.spec.ts` — un-skip both specs. Spec 1 declared before
  spec 2, since spec 2 dirties the tenant. The two specs that assert on the
  *published question set* keep working against either tenant, but they now run
  under the blank identity too — check nothing in them depends on the seeded DNA.
- `web/.env.local.example` — document `E2E_CLERK_BLANK_USER_EMAIL` and
  `E2E_CLERK_BLANK_ORG_ID`.

### Known limitation, accepted

Re-running `make test-e2e` without restarting the stack fails spec 1, because
spec 2 left the tenant filled in. Accepted rather than solved: the alternative
is a Playwright `globalSetup` that shells out to the seed, which drags a
database dependency into the web suite that it has so far stayed clean of.
Spec 1 should fail with a message naming `make e2e-up`, not a bare assertion
failure, so the cause is obvious.

## Acceptance criteria

- [x] Required-field gating in onboarding is covered by a test that actually runs. — `onboarding.spec.ts:60`, passing in the `chromium-onboarding` project.
- [x] The wizard's full happy path — answering through to the Brand screen — is covered by a test that actually runs. — `onboarding.spec.ts:106`, passing.
- [x] Neither test destabilises the campaign specs sharing the seeded tenant, under `fullyParallel`. — they run against a *different* tenant in their own project; the 38 `chromium` specs pass alongside them.
- [x] `web/tests/onboarding.spec.ts` contains no `test.skip`. — `grep -c "test.skip"` returns 0.
- [x] The seed establishes the blank tenant's blankness on every stack start, including after a run that filled it in. — `test_reseeding_blanks_a_tenant_the_wizard_filled_in`, and observed live: after a run that completed the wizard, re-running the seed left 0 `dna_answers` and no `dna.md`.
- [x] Spec 2 proves a `q_business_name` answer overrides the organization name on the Brand screen. — the spec answers `Peakline Roasters`; the tenant row is named `e2e-blank-tenant-<n>`. Confirmed in the database after a run.
- [x] Spec 1 fails with a message naming `make e2e-up` when the tenant is not blank, rather than a bare assertion failure. — fired verbatim during verification, printing `Received: "Acme Coffee"` alongside it.
- [x] `make test-e2e` passes with the skip count reduced to zero. — **43 passed, 0 failed, 0 skipped** in 46.1s.
- [x] Web gates pass — `pnpm typecheck`, `pnpm lint`, `pnpm format:check`, `pnpm test:unit` (43 unit tests).
- [x] Harness gates pass — `uv run ruff check .`, `uv run mypy src`, `uv run pytest` (**586 passed**).

**Landed in `63992a7`.**

## Suspected location

- [`web/tests/onboarding.spec.ts`](../../../../web/tests/onboarding.spec.ts) — the two skips and the comments explaining them.
- [`agent-harness/scripts/seed_test_tenant.py`](../../../../agent-harness/scripts/seed_test_tenants.py) — `TEST_TENANT_ID` is a single hardcoded constant, so a second tenant is a change here.
- [`web/tests/auth.setup.ts`](../../../../web/tests/auth.setup.ts) — signs into one organization and writes one storage state.
- [`web/playwright.config.ts`](../../../../web/playwright.config.ts) — one `setup` project feeding one `chromium` project; a second identity means a second pair.

## Comments

**2026-09-04.** Filed while closing [12](12-remaining-screens-wired.md).
Both specs predate the seed: they were written in
[web-mockup](../../../web-mockup/issues/archive/08-onboarding-wizard.md) against a
tenant that had no Brand DNA at all, and only became unrunnable when
[13](13-frontend-suite-cannot-run-without-credentials.md) gave the suite
a real tenant to work against. Worth remembering that the seed did not break
them — it revealed that they had never shared a fixture with anything else.

Related and worth folding into whatever fix lands: test campaigns **accumulate**
in the shared tenant across runs, so any spec asserting on a campaign *name*
rather than its slug gets flakier the longer the tenant lives. The specs written
in slice 12 assert on slugs for exactly this reason, but nothing enforces it.

**2026-09-04 (triage, grilling paused mid-way).** Two findings and one
recommendation, none of them yet a decision:

- The issue understates option A. The seed pairs a tenant to a Clerk
  *organization* (`external_auth_id`), while `auth.setup.ts` signs a *user* in
  by email, and `web/src/lib/engine.ts` passes a Clerk token the engine resolves
  the tenant from. So a second identity means a second org **and** either a
  second test user or org-switching inside the auth fixture — not just a second
  storage state.
- The two specs are not the same cost. Spec 1 only *reads* a blank tenant; spec
  2 *fills it in*, so it needs blanking per run, not merely a blank tenant once.
  That collapses if the blank tenant is re-blanked by the seed on every stack
  start — it is load-bearing for nothing, so re-seeding it is safe in a way
  re-seeding the shared tenant is not.
- Recommended shape (not agreed): one mechanism, a second Clerk test user in a
  second org, `auth.setup.ts` looping over two `{email, storageState}` pairs,
  and the seed writing a second tenant row with zero `dna_answers`. Rejected
  same-user-two-orgs because org-switching becomes permanent machinery in the
  most flake-sensitive part of the suite.

**Open question, unanswered:** should `seed_test_tenant.py` seed both tenants in
one invocation, or take `--blank`/`--tenant-id` and be called twice from compose?

**2026-09-05 (grilling, complete — issue is now `ready-for-agent`).** Six
decisions, with the reasoning worth keeping:

- **Correction to the 2026-09-04 note.** It said a second identity needs a
  second org *and* either a second user or org-switching. Reading
  `adapters/auth.py` and `web/src/lib/engine.ts`: the tenant comes from the
  `org_id` claim on the session token, which carries the session's *active*
  organization. So the org is the only real axis, and a second user is one way
  to fix that claim — the cheapest, but a choice rather than a requirement.
  Rejected same-user-two-orgs on the original grounds: org-switching becomes
  permanent machinery in the most flake-sensitive part of the suite, and a
  session token that has not refreshed its `org_id` writes to the *wrong*
  tenant — a failure that reads as a data bug, not an auth bug.
- **Auto-provisioning was considered and rejected** (decision 2). It works —
  `PostgresTenantDirectory.resolve` mints a fresh row with zero `dna_answers`
  for an unknown org — and it would even exercise the true first-sign-in path.
  Rejected because the tenant id would be random, discoverable only by joining
  through the Clerk org id, which is exactly the problem the seed script's
  docstring says it exists to avoid. Second reason: with auto-provisioning the
  blank tenant does not exist until someone signs in, so there is no reliable
  moment to blank it.
- **Blanking must delete two things, not one** (decision 3). The wizard's resume
  point is computed from `dna_answers`, but the DNA Gate and the segment parser
  read the rendered `dna.md` document (ADR-0018). A `seed_blank` that clears
  only the answers leaves a tenant whose wizard looks empty and whose gate
  passes.
- **Serial execution is honest, not a workaround** (decision 4). The two specs
  share a mutable fixture: spec 1 reads a blank tenant, spec 2 fills it in.
  Saying so in the config beats a `beforeEach` that would need either a
  test-only DNA-wipe endpoint shipped in the product or a database client in the
  web suite.
- **Spec 2's business name is load-bearing** (decision 5). If the blank tenant
  were seeded as "Acme Coffee" too, the Brand assertion would pass whether or
  not the wizard wrote anything — a test that cannot fail for the reason it
  exists. Seeding a different name makes it a real test of the
  answer-wins-over-org-name rule in `questionnaire/render.py`.
- **No ADR, no `CONTEXT.md` change.** The decision is reversible, local to the
  test suite, and introduces test-fixture vocabulary rather than domain
  vocabulary. `CONTEXT.md` is a glossary of the domain and should stay one.

**Open question from 2026-09-04, now answered:** the seed takes no `--blank` or
`--tenant-id` arguments and is called once — see decision 3.

**2026-09-05 (implementation, `63992a7`).** Four corrections to what this issue
assumed, all found by running the thing:

- **The wizard does not resume on the first unanswered step.** Both the Symptom
  and decision 4 say it does. `useWizard` (`web/src/components/wizard/use-wizard.ts`)
  always starts at step 0. The *effect* the issue describes is real — a complete
  DNA pre-fills step 1, so *Next →* succeeds and the refusal never fires — but
  the cause is pre-filled fields, not a resume point. Spec 1's guard therefore
  checks that the first field is empty, not that the wizard is on step 1: `Step
  1 of 5` renders for a filled tenant too, so a guard on it would never fire.
- **`workers: 1` does not guarantee declaration order.** Decision 4 asks for the
  specs to "run serially", and the config's `fullyParallel: false` plus one
  worker looked like enough. It is not — Playwright still reordered them, and
  the spec that fills the tenant in ran *first*, so spec 1 found "Acme Coffee"
  waiting for it. `test.describe.configure({ mode: "serial" })` in the spec file
  is the actual guarantee. The same bug hit `auth.setup.ts`, where the two
  sign-ins raced and corrupted each other's storage state.
- **Decision 5 was defeated by a spec neither decision mentions.** The spec
  between the two un-skipped ones (`answers save partway and are still there on
  return`) writes `q_business_name = "Acme Coffee"` and it persists. Under
  serial declaration order, spec 2's Brand assertion would then pass whether or
  not its own answers landed — exactly the tautology decision 5 exists to
  prevent. Spec 2 now answers `Peakline Roasters`, a name only it writes. Caught
  in code review, not by the suite, which was green and meaningless.
- **One assertion had rotted while skipped.** Spec 2 asserted on `Last verified
  Just now`, text that exists nowhere in `web/src/` — it was written against the
  web-mockup Brand screen and never updated. It now asserts `Every Required
  answer is in`, which `brand-screen.tsx` renders only when the DNA Gate passes.
  This is the clearest argument for the issue's own premise: a skipped spec
  stops being a test and nobody finds out.

**Known limitation, still accepted and now observed.** Re-running the suite
against a live stack without re-seeding fails spec 1, as predicted. The guard
message names `make e2e-up` and prints the offending value, which made the cause
obvious on sight. A faster path than a full restart, if it becomes annoying:
`docker compose --env-file web/.env.local -f docker-compose.e2e.yml up -d
--force-recreate seed` re-establishes both tenants in about five seconds.

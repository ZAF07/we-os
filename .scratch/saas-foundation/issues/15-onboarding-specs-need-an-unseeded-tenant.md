# 15 — Two onboarding specs are permanently skipped, so the wizard's gating is untested

Status: needs-triage
Type: task

## Parent

[PRD: we-OS SaaS foundation](../PRD.md) · follows [13 — the e2e stack](archive/13-frontend-suite-cannot-run-without-credentials.md)

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
([13](archive/13-frontend-suite-cannot-run-without-credentials.md)), and both
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

A tenant the onboarding specs can start from empty, without disturbing the one
every other spec depends on. Worth deciding rather than assuming:

- **A second Clerk organization**, seeded with *no* Brand DNA, that
  `auth.setup.ts` can also sign into — the honest option, since it exercises the
  real onboarding path end to end. Needs a second organization on the shared
  test instance and a second storage state, and `seed_test_tenant.py` currently
  hardcodes one `TEST_TENANT_ID`.
- **Reset-and-restore around the specs**, running them serially in their own
  project so they can blank the DNA and put it back. Cheaper, but a crashed run
  leaves the shared tenant empty and every other spec then fails at the gate —
  the failure mode is bad enough to weigh carefully.
- **Cover it below the browser instead** — a unit test over the wizard's
  step-completeness logic, plus the engine-side completeness report, which is
  already covered. Cheapest, and honest about what it does *not* prove: that the
  button is actually disabled in a real browser.

The first is the only one that tests what the specs claim to test. The third is
the one that could land today. That trade is the decision this issue needs.

## Acceptance criteria

- [ ] Required-field gating in onboarding is covered by a test that actually runs.
- [ ] The wizard's full happy path — answering through to the Brand screen — is covered by a test that actually runs.
- [ ] Neither test destabilises the campaign specs sharing the tenant, under `fullyParallel`.
- [ ] `web/tests/onboarding.spec.ts` contains no `test.skip`, or each remaining one names a reason that is still true.
- [ ] `make test-e2e` passes with the skip count reduced.
- [ ] Web gates pass — `pnpm typecheck`, `pnpm lint`, `pnpm format:check`, `pnpm test:unit`.

## Suspected location

- [`web/tests/onboarding.spec.ts`](../../../web/tests/onboarding.spec.ts) — the two skips and the comments explaining them.
- [`agent-harness/scripts/seed_test_tenant.py`](../../../agent-harness/scripts/seed_test_tenant.py) — `TEST_TENANT_ID` is a single hardcoded constant, so a second tenant is a change here.
- [`web/tests/auth.setup.ts`](../../../web/tests/auth.setup.ts) — signs into one organization and writes one storage state.
- [`web/playwright.config.ts`](../../../web/playwright.config.ts) — one `setup` project feeding one `chromium` project; a second identity means a second pair.

## Comments

**2026-09-04.** Filed while closing [12](archive/12-remaining-screens-wired.md).
Both specs predate the seed: they were written in
[web-mockup](../../web-mockup/issues/archive/08-onboarding-wizard.md) against a
tenant that had no Brand DNA at all, and only became unrunnable when
[13](archive/13-frontend-suite-cannot-run-without-credentials.md) gave the suite
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

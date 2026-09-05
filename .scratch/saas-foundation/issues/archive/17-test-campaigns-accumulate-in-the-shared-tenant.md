# 17 — Test campaigns accumulate in the shared tenant, and nothing keeps specs off names

Status: completed
Type: task

## Parent

[PRD: we-OS SaaS foundation](../PRD.md) · split out of [15](15-onboarding-specs-need-an-unseeded-tenant.md)

## Symptom

`seed_test_tenant.py` is idempotent about the Brand DNA — re-running it leaves
the same tenant with the same answers — but it says nothing about **campaigns**.
Every spec that creates one leaves it behind, so the seeded tenant's campaign
list grows by a few rows on every `make test-e2e`.

Two consequences, one mild and one not:

- **Mild.** The Campaigns table gets longer over the life of the test instance.
  Specs that assert on a row they just created still pass; they just do it
  against a busier screen, and pagination or ordering could eventually put the
  new row somewhere a spec does not look.
- **The real one.** A spec that asserts on a campaign **name** rather than its
  slug gets steadily flakier: the second run has two campaigns matching the
  name, and a `getByText` that resolved uniquely on a fresh tenant becomes a
  strict-mode violation. The specs written in
  [12](12-remaining-screens-wired.md) assert on slugs for exactly this
  reason — but that is a convention held in one author's head, not a rule
  anything enforces. The next spec written against a freshly-seeded tenant will
  pass, and start failing for someone else a week later.

## Repro

```bash
make e2e-up && make test-e2e     # note the campaign count
make test-e2e                    # same stack, no re-seed — count has grown
```

Then add a spec asserting on a campaign name rather than a slug: green on the
first run, strict-mode violation on the second.

## What's needed

Two halves, decidable separately:

**Stop the accumulation.** Either the seed purges the test tenant's campaigns
(and their documents, runs, and checkpoint threads) on every stack start —
symmetric with how it already rewrites the DNA — or the suite cleans up after
itself per spec. The seed-time purge is the simpler of the two and matches the
existing "the stack establishes fixture state on start" model, but it is a
wider delete than the seed currently does and wants care about what a campaign
actually owns.

**Stop names being asserted on.** A convention nothing enforces will be broken.
Options: a lint rule over `web/tests/`, a shared helper that mints a
run-unique campaign name so name assertions become safe, or a documented note in
the suite's README accepting that this stays a review-time check.

Worth deciding whether the second half is worth machinery at all, or whether
purging on start makes name assertions safe enough in practice.

## Acceptance criteria

- [x] A second `make test-e2e` against a re-seeded stack sees the same campaign count as the first. — two consecutive full runs each left **23 campaign documents and 4 runs**, counted in Postgres.
- [x] Whatever a campaign owns — documents, runs, checkpoint threads — is purged with it, not orphaned. — five tables, not three: `documents` (under `campaigns/`), `runs`, `deliverable_versions`, `usage_ledger`, and the three checkpoint tables by `<tenant>/%` thread prefix. After a re-seed: **0 campaign docs, 0 runs, 0 checkpoints, `dna.md` intact**.
- [x] Either name-based assertions are made safe, or the convention is enforced or explicitly documented as a review-time check. — both: `uniqueName` in `web/tests/fixtures.ts` mints run-unique text, and an ESLint `no-restricted-syntax` rule over `tests/**` refuses an inline `Date.now()`. See the caveat under Comments.
- [x] `make test-e2e` passes. — **43 passed, 0 failed, 0 skipped**.

**Landed in `63992a7`** (together with [15](15-onboarding-specs-need-an-unseeded-tenant.md) — the purge lives inside the same two seed functions that issue introduced, so splitting the commit would have meant landing one with failing tests).

## Suspected location

- [`agent-harness/scripts/seed_test_tenant.py`](../../../../agent-harness/scripts/seed_test_tenants.py) — idempotent about DNA, silent about campaigns.
- [`docker-compose.e2e.yml`](../../../../docker-compose.e2e.yml) — where the seed runs on stack start.
- `web/tests/*.spec.ts` — the specs creating campaigns.

## Comments

**2026-09-05.** Split out of [15](15-onboarding-specs-need-an-unseeded-tenant.md),
where it was noted in passing on 2026-09-04 while closing
[12](12-remaining-screens-wired.md). Kept separate deliberately: it
touches the same files as 15 but solves an unrelated problem, and would exist
even if the onboarding specs did not. Folding it in would have made 15's
acceptance criteria stop describing one thing.

Note the interaction with 15: the **blank** tenant introduced there is purged of
its DNA on every stack start, so if the campaign purge lands too, both test
tenants get the same treatment and the seed becomes uniformly "establish fixture
state", which is a tidier thing to explain than what it does today.

**2026-09-05 (implementation, `63992a7`).** Both halves landed. Notes worth
keeping:

- **A campaign owns more than this issue listed.** "Documents, runs, and
  checkpoint threads" missed `deliverable_versions` and `usage_ledger`, both
  tenant-and-slug partitioned. The purge deletes all five. Leaving the
  checkpoint threads would have been the sharp one: a new campaign given a slug
  a previous run used would *resume* the old run's state rather than start
  clean.
- **The purge is scoped twice.** By tenant, so pointing the seed at anything
  other than the disposable stack cannot sweep a real business's campaigns; and
  for documents by path prefix, so `dna.md` survives — deleting it would halt
  every campaign spec at the Stage 0 gate, which the seed exists to let them
  through.
- **The lint rule enforces the old spelling's absence, not the new convention's
  presence.** Code review made this point and it is correct: the rule refuses an
  inline `Date.now()`, which is how every spec previously minted a unique name,
  but nothing stops someone hardcoding `"Autumn Referral Push"` with no suffix.
  Accepted rather than solved — catching that needs either a much cleverer rule
  or a genuine review-time check, and `web/README.md` documents the convention
  for the latter. Worth revisiting only if it actually bites.
- **The seed now reads uniformly as "establish fixture state".** As the note
  above anticipated: both tenants get their campaigns purged, the seeded one
  gets its DNA rewritten, the blank one gets its DNA deleted. That is a simpler
  sentence than what the seed did before, which is the real win here.

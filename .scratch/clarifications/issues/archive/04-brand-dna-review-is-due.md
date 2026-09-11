# 04 — Brand DNA review is due

Status: completed
Type: task

## Parent

[PRD: Clarifications](../../PRD.md) · [ADR-0028](../../../../docs/adr/0028-clarifications-are-brand-dna-the-specialist-asks-for.md)

## What to build

The platform tells the business owner, in the app, when it is time to look at their Brand DNA again.

The tenant record gains a reviewed-at timestamp. A review is **due** when now minus reviewed-at exceeds a new interval setting, one minute in dev and a week in production. A tenant that has never reviewed counts from when its DNA was first completed. Reviewed-at is set by a new mark-reviewed endpoint and by saving any questionnaire or Clarification answer, so the owner is never asked to review what they just edited.

On Home, the Action Queue shows an amber **Review** item when a review is due, linking to the Brand page. The Brand page shows a Reviewed action while a review is due; clicking it clears the item. The empty-state copy names a due review as one reason an item appears.

Due-ness is derived from the timestamp on every read, never stored, so the item cannot drift from the truth. This issue does not send email; the next one does, from the same timestamp.

## Acceptance criteria

- [x] The Home payload carries a Review item exactly when now minus reviewed-at exceeds the configured interval, with a fake clock in the API tests.
- [x] Mark-reviewed, saving a questionnaire answer, and saving a Clarification answer each clear the item.
- [x] A tenant whose DNA was just completed is not due until the interval has passed.
- [x] The interval is read from settings; changing it changes due-ness on the next read with no restart of the test app.
- [x] Home shows the amber Review item in the browser suite; the Brand page's Reviewed action clears it.
- [x] `make check` and `make test-postgres` pass; `make test-e2e` passes; the item and the Reviewed action are confirmed in the running app.

## Blocked by

None - can start immediately.

## Comments

**2026-09-11 — plan (agent).** Branch `feat/clarifications-04-review-due`, worked in a scratchpad worktree.

- Settings: `dna_review_interval` from `MARKETING_OS_DNA_REVIEW_INTERVAL`, a duration such as `7d`, `1m`, `20s` or bare seconds. Default a week; the dev compose passes `1m`, the e2e compose `20s`.
- Domain: `questionnaire/review.py` holds one pure function. A review is due when the DNA is complete and now minus the last review exceeds the interval. The last review is the tenant's `dna_reviewed_at`, or when it has none, when its answers were last saved — the closest thing to "when the DNA was first completed" for a tenant seeded or migrated without one. Never stored.
- Port: `Tenant.dna_reviewed_at`; `TenantDirectory.mark_dna_reviewed(tenant_id, at=...)` on the in-memory and Postgres directories; the passthrough directory accepts and keeps nothing, as it does for the tier. Postgres gains the column through `ADD COLUMN IF NOT EXISTS`, which the drift check picks up on its own.
- API: `GET /brand-dna/review` reports `{due, reviewed_at}`; `POST /brand-dna/review` marks it. Saving or deleting a questionnaire answer, editing a Clarification, and answering a run's questions all mark it too. The clock is one seam, `get_clock`, so the API tests drive a fake one.
- Seed: the seeded e2e tenant is written with a reviewed-at a month old, so the review is due from the first request and again after every reset; the blank tenant has none.
- Web: `getDnaReview` / `markDnaReviewed`; Home's queue gains an amber Review item linking to `/brand`; the Brand screen shows a banner with a Reviewed button while due; the empty-state copy names a due review.
- Tests: config parse; the pure function; directories (in-memory, passthrough, Postgres); API with a fake clock — due exactly past the interval, cleared by each of the four writes, not due right after completing, and the interval re-read from settings; vitest for the queue and the banner; `review.spec.ts` on the compose stack, which polls for due-ness because other specs' saves clear it and the 20 s interval brings it back.

**2026-09-11 — review (agent).** Standards and spec reviews on `b908f63`. Resolved: one `nullOnEngineError` in the engine client, used by Home and the Brand page; one `iso_z` timestamp renderer shared by the answer stores and the review payload; the passthrough directory builds its tenant through one helper and its docstring states plainly that a review cannot be cleared on that layer; `_now()` hides the clock's double call; the queue's review item is named as one and the review argument is required; the test's wait helper imports at the top and documents what it raises. Decisions kept, on purpose: a business that never marked a review counts from when its answers were *last saved* — the closest stored fact to "when its DNA was first completed", which nothing records, and the only case it applies to is a tenant seeded or migrated without a review, since every save now records one; an incomplete DNA is never due, because the Setup item already stands for it; deleting an answer counts as a review, since it is an edit of the DNA; the settings cache is cleared by the test rather than per request, so a deployment changes the interval with a restart, which the criterion scopes to the test app. The `//` comments in the Playwright specs match every other spec there.

**2026-09-11 — done (agent).** Gates on the final tree (`f722148`): `make check` 747 passed; `make test-postgres` 871 passed; `make test-e2e` 75 passed in 1.2 min, including the new `review.spec.ts`. A first e2e run on `b908f63` failed six unrelated specs with two-minute `page.goto` stalls and clicks that never navigated, while the machine's load average sat at 68 and `next build` took 2.3 min; the review spec passed in that run too, and the rerun on a quiet machine passed in full. Not built here, by design: the reminder email and its loop (issue 05).

## Completion

- Completed: 2026-09-11
- Commits: `b908f63` Tell the business when its Brand DNA is due a review; `f722148` Tighten the Brand DNA review after review; on branch `feat/clarifications-04-review-due`; status commit and merge recorded below once made.
- Evidence per criterion:
  - Home payload carries a Review item exactly when now minus reviewed-at exceeds the interval, fake clock — the engine's `GET /brand-dna/review` reports `due` from `questionnaire/review.py::dna_review`, derived on every read; `tests/test_dna_review.py::test_a_review_is_due_once_more_than_the_interval_has_passed`, `::test_a_review_is_not_due_at_exactly_the_interval` (pure), `::test_a_dna_just_completed_is_not_due_until_the_interval_has_passed` and `::test_marking_reviewed_clears_it_for_another_interval` (API, `FakeClock`); `web/src/lib/home.test.ts` "adds an amber Review item leading to the Brand page when a review is due", "adds nothing when no review is due, or the review could not be read", "puts the review after decisions and before stale work".
  - Mark-reviewed, saving a questionnaire answer, and saving a Clarification answer each clear the item — `::test_marking_reviewed_clears_it_for_another_interval`, `::test_saving_a_questionnaire_answer_counts_as_a_review`, `::test_deleting_an_answer_counts_as_a_review_too`, `::test_editing_a_clarification_counts_as_a_review`, `::test_answering_a_runs_questions_counts_as_a_review`.
  - A tenant whose DNA was just completed is not due until the interval has passed — `::test_a_dna_just_completed_is_not_due_until_the_interval_has_passed` (false at completion, false at exactly a week, true a second later).
  - The interval is read from settings; changing it changes due-ness on the next read with no restart of the test app — `::test_the_interval_is_read_from_settings_on_every_read`; parsing in `::test_the_interval_is_written_as_a_duration`, `::test_a_duration_that_is_not_one_is_refused`, `::test_the_review_interval_defaults_to_a_week`, `::test_the_review_interval_is_read_from_the_environment`.
  - Home shows the amber Review item in the browser suite; the Brand page's Reviewed action clears it — `web/tests/review.spec.ts` on the compose stack (item with `text-amber-800`, link to `/brand`, banner, Reviewed click, item gone; passed in both e2e runs); `web/src/components/brand/review-banner.test.tsx` (shown when due, hidden after marking, error kept, next review shown again).
  - `make check`, `make test-postgres`, `make test-e2e` pass on `f722148`; the item and the Reviewed action are confirmed in the running app by the e2e spec above. Storage: `tests/test_postgres.py::test_a_dna_review_is_recorded_and_read_back_by_every_path`, `::test_a_review_cannot_be_recorded_for_a_tenant_that_does_not_exist`; seed: `tests/test_seed_test_tenants.py::test_the_seeded_tenant_is_due_a_review_and_the_blank_one_is_not`, `::test_reseeding_puts_the_review_back_in_the_past`.

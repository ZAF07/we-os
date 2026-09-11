# 04 — Brand DNA review is due

Status: ready-for-agent
Type: task

## Parent

[PRD: Clarifications](../PRD.md) · [ADR-0028](../../../docs/adr/0028-clarifications-are-brand-dna-the-specialist-asks-for.md)

## What to build

The platform tells the business owner, in the app, when it is time to look at their Brand DNA again.

The tenant record gains a reviewed-at timestamp. A review is **due** when now minus reviewed-at exceeds a new interval setting, one minute in dev and a week in production. A tenant that has never reviewed counts from when its DNA was first completed. Reviewed-at is set by a new mark-reviewed endpoint and by saving any questionnaire or Clarification answer, so the owner is never asked to review what they just edited.

On Home, the Action Queue shows an amber **Review** item when a review is due, linking to the Brand page. The Brand page shows a Reviewed action while a review is due; clicking it clears the item. The empty-state copy names a due review as one reason an item appears.

Due-ness is derived from the timestamp on every read, never stored, so the item cannot drift from the truth. This issue does not send email; the next one does, from the same timestamp.

## Acceptance criteria

- [ ] The Home payload carries a Review item exactly when now minus reviewed-at exceeds the configured interval, with a fake clock in the API tests.
- [ ] Mark-reviewed, saving a questionnaire answer, and saving a Clarification answer each clear the item.
- [ ] A tenant whose DNA was just completed is not due until the interval has passed.
- [ ] The interval is read from settings; changing it changes due-ness on the next read with no restart of the test app.
- [ ] Home shows the amber Review item in the browser suite; the Brand page's Reviewed action clears it.
- [ ] `make check` and `make test-postgres` pass; `make test-e2e` passes; the item and the Reviewed action are confirmed in the running app.

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

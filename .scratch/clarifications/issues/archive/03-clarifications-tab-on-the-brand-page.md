# 03 — Clarifications tab on the Brand page

Status: completed
Type: task

## Parent

[PRD: Clarifications](../../PRD.md) · [ADR-0028](../../../../docs/adr/0028-clarifications-are-brand-dna-the-specialist-asks-for.md)

## What to build

The business owner can see and correct every fact a specialist ever asked them for.

The Brand page gains a **Clarifications** tab listing each Clarification with its question, the reason it was asked, which stage and campaign asked it, and the answer. Each answer can be edited inline and saved. A new endpoint updates one Clarification's answer.

An edit is retrospective. It writes to the Brand DNA only: no campaign is re-run, no deliverable is marked stale, no run is touched. Staleness stays a property of deliverable versions and nothing here writes one.

When the tenant has no Clarifications, the tab says so and explains that questions a specialist asks during a campaign will appear here.

## Acceptance criteria

- [x] The DNA read reports each Clarification with question, reason, origin stage and campaign, and answer.
- [x] Editing an answer through the API changes the rendered DNA and nothing else: every campaign's deliverables, versions, stale flags and run statuses are identical before and after.
- [x] The Brand page's Clarifications tab lists the answers and an inline edit saves and re-renders.
- [x] The empty state is shown for a tenant with no Clarifications.
- [x] `make check` and `make test-postgres` pass; `make test-e2e` passes; the tab is confirmed in the running app.

## Blocked by

- [02 — The owner answers and the campaign continues](02-the-owner-answers-and-the-campaign-continues.md)

## Comments

**2026-09-11 — plan (agent).** Branch `feat/clarifications-03-clarifications-tab`, worked in a scratchpad worktree.

- Port: `AnswerStore.update_clarification(tenant, clarification_id, answer)` on the in-memory and Postgres stores. Raises `DocumentNotFoundError` when the tenant has no such Clarification, so another business's id reads as missing. The edit refreshes `answered_at`; order and every other field stay as they were.
- API: `PUT /brand-dna/clarifications/{id}` with `{"answer"}`. 404 unknown or foreign id; 422 blank. Re-projects `dna.md` through the same path a questionnaire save uses, and touches nothing else: no campaign, deliverable, version, stale flag or run.
- Web: `Clarification` type on `BrandDna`; a `saveClarificationAnswer` server action; the Brand screen gains a Clarifications tab after the questionnaire sections listing question, reason, origin stage and campaign, and answer, with inline edit and save. Empty state explains where Clarifications come from.
- Tests: store (in-memory and Postgres, including tenant scoping), API (edit changes the DNA read and nothing else, measured as a before/after snapshot of every campaign read and the run status; refusals), vitest for the tab, and the clarifications e2e spec extended to check the empty state before the run and the tab's list and edit after the answer.

**2026-09-11 — review (agent).** Standards and spec reviews on `32157e9`. Resolved: the Brand screen now switches on the tab explicitly and returns the Clarifications panel early, with the section nav extracted so the questionnaire body is untouched; Save/Cancel is one shared `EditActions` used by both cards; the tab renders from its props with the last saved answer laid over them, so a refresh can bring new Clarifications in; the "nothing else changes" API test now also reads each deliverable's current content and every version's content. Kept, on purpose: an edit refreshes `answered_at`, since the field means when the answer was given and issue 04 counts a Clarification save as a review; the count badge on the tab.

**2026-09-11 — done (agent).** Gates on the final tree (`8c5c088`): `make check` 710 passed; `make test-postgres` 829 passed (a first run alongside the e2e build failed one pre-existing auth test, `test_logs_the_failure_class_and_path_when_a_token_has_expired`, which stamps `iat` from the wall clock and asserts `iat=+0s`; a second run on an idle machine passed in full); `make test-e2e` 74 passed, including the extended `clarifications.spec.ts`, which checks the empty state before the run, then after the answer finds it on the tab with its reason and origin, corrects it, sees the correction survive a reload, and finds the campaign still at the gate it had reached. Not built here, by design: the review reminder and its Review item (issues 04–05).

## Completion

- Completed: 2026-09-11
- Commits: `32157e9` Let the business see and correct every Clarification on the Brand page; `8c5c088` Tighten the Clarifications tab after review; on branch `feat/clarifications-03-clarifications-tab`. Status commit and merge commit: see below.
- Evidence per criterion:
  - DNA read reports question, reason, origin stage and campaign, and answer — `GET /brand-dna` dumps every `Clarification` field (`app.py`, `brand_dna`); asserted in `tests/test_clarifications.py::test_answering_saves_the_clarifications_and_the_run_continues_to_its_next_gate` (`question`, `answer`, `reason`, `stage`, `slug`, `id`).
  - Editing changes the rendered DNA and nothing else — `::test_editing_a_clarification_changes_the_dna_and_nothing_else`: a before/after snapshot of the campaign, its stages, the deliverable listing with each deliverable's current content and every version's content, the run, the run list and the completeness report is byte-identical, while the DNA read, its markdown and the tenant's `dna.md` carry the new answer. Refusals: `::test_editing_a_clarification_the_business_does_not_have_is_404`, `::test_a_blank_edit_is_refused_and_the_answer_stands`, `::test_one_business_cannot_edit_anothers_clarification`. Stores: `tests/test_questionnaire.py::test_answer_store_edits_one_clarification_answer_and_leaves_the_rest` and `::test_answer_store_refuses_to_edit_a_clarification_the_business_does_not_have`; `tests/test_postgres.py::test_a_clarification_answer_can_be_edited_in_place` and `::test_one_business_cannot_edit_anothers_clarification`.
  - The tab lists the answers and an inline edit saves and re-renders — `web/src/components/brand/clarifications-tab.test.tsx` (list with question, reason, origin and answer; save in place; blank refused; failed save kept open); `web/tests/clarifications.spec.ts` on the compose stack (list, edit, reload).
  - Empty state for a tenant with no Clarifications — `clarifications-tab.test.tsx` ("explains where Clarifications come from when there are none"); `clarifications.spec.ts` before the run halts.
  - `make check`, `make test-postgres`, `make test-e2e` pass on `8c5c088`; the tab is confirmed in the running app by the e2e spec above.

# 03 — Clarifications tab on the Brand page

Status: ready-for-agent
Type: task

## Parent

[PRD: Clarifications](../PRD.md) · [ADR-0028](../../../docs/adr/0028-clarifications-are-brand-dna-the-specialist-asks-for.md)

## What to build

The business owner can see and correct every fact a specialist ever asked them for.

The Brand page gains a **Clarifications** tab listing each Clarification with its question, the reason it was asked, which stage and campaign asked it, and the answer. Each answer can be edited inline and saved. A new endpoint updates one Clarification's answer.

An edit is retrospective. It writes to the Brand DNA only: no campaign is re-run, no deliverable is marked stale, no run is touched. Staleness stays a property of deliverable versions and nothing here writes one.

When the tenant has no Clarifications, the tab says so and explains that questions a specialist asks during a campaign will appear here.

## Acceptance criteria

- [ ] The DNA read reports each Clarification with question, reason, origin stage and campaign, and answer.
- [ ] Editing an answer through the API changes the rendered DNA and nothing else: every campaign's deliverables, versions, stale flags and run statuses are identical before and after.
- [ ] The Brand page's Clarifications tab lists the answers and an inline edit saves and re-renders.
- [ ] The empty state is shown for a tenant with no Clarifications.
- [ ] `make check` and `make test-postgres` pass; `make test-e2e` passes; the tab is confirmed in the running app.

## Blocked by

- [02 — The owner answers and the campaign continues](02-the-owner-answers-and-the-campaign-continues.md)

## Comments

**2026-09-11 — plan (agent).** Branch `feat/clarifications-03-clarifications-tab`, worked in a scratchpad worktree.

- Port: `AnswerStore.update_clarification(tenant, clarification_id, answer)` on the in-memory and Postgres stores. Raises `DocumentNotFoundError` when the tenant has no such Clarification, so another business's id reads as missing. The edit refreshes `answered_at`; order and every other field stay as they were.
- API: `PUT /brand-dna/clarifications/{id}` with `{"answer"}`. 404 unknown or foreign id; 422 blank. Re-projects `dna.md` through the same path a questionnaire save uses, and touches nothing else: no campaign, deliverable, version, stale flag or run.
- Web: `Clarification` type on `BrandDna`; a `saveClarificationAnswer` server action; the Brand screen gains a Clarifications tab after the questionnaire sections listing question, reason, origin stage and campaign, and answer, with inline edit and save. Empty state explains where Clarifications come from.
- Tests: store (in-memory and Postgres, including tenant scoping), API (edit changes the DNA read and nothing else, measured as a before/after snapshot of every campaign read and the run status; refusals), vitest for the tab, and the clarifications e2e spec extended to check the empty state before the run and the tab's list and edit after the answer.

**2026-09-11 — review (agent).** Standards and spec reviews on `32157e9`. Resolved: the Brand screen now switches on the tab explicitly and returns the Clarifications panel early, with the section nav extracted so the questionnaire body is untouched; Save/Cancel is one shared `EditActions` used by both cards; the tab renders from its props with the last saved answer laid over them, so a refresh can bring new Clarifications in; the "nothing else changes" API test now also reads each deliverable's current content and every version's content. Kept, on purpose: an edit refreshes `answered_at`, since the field means when the answer was given and issue 04 counts a Clarification save as a review; the count badge on the tab.

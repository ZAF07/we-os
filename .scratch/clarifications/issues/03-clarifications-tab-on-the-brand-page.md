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

# 02 — Home screen + shared primitives

Status: completed
Type: task

## Parent

[PRD: Marketing OS web frontend — Milestone 1](../PRD.md)

## What to build

The Home screen, rendered entirely from mock fixtures, plus the shared UI primitives it establishes for the rest of the app: **StatusPill** (reads the canonical status taxonomy from slice 01), **Card**, and **StatCard**. Later screens reuse these.

End-to-end behavior: the operator lands on Home and sees four stat cards (Pending approvals, Active campaigns, Scheduled this week, Blocked), a prioritized decision/approval queue, an active-campaigns list, a blocked list, and the upcoming-items / findings / performance-stats / recommendations panels. Queue items carry typed tags (Decision, Flagged, Needs input), context, a due label, and a CTA that navigates to the right place — a Decision to a Workspace, a Flagged claim to the relevant Brand section (target section exists in slice 06; wire the link now). The pending-approvals stat and queue reflect the store's `approved` flag (so slice 04's approve action will visibly change them).

Use the exact Fernway data and copy from the prototype's `renderVals()` (`homeStats`, `queueAll`, `activeCampaigns`, `blocked`, `upcoming`, `findings`, `perfStats`, `recos`).

## Acceptance criteria

- [x] StatusPill, Card, StatCard primitives exist; StatusPill derives its colors from the slice-01 taxonomy (no per-screen color literals).
- [x] Home renders all sections from fixtures: stat cards, decision/approval queue, active campaigns, blocked, upcoming, findings, performance stats, recommendations.
- [x] Queue items show the correct tag, context line, due label, and CTA; each CTA navigates to its target route (Workspace, or a Brand section deep-link).
- [x] Pending-approvals count and the queue read from the store's `approved` flag.
- [x] A Playwright smoke test asserts Home renders its headline sections and a queue CTA navigates.
- [x] typecheck / lint / Prettier pass.

## Blocked by

- [01 — Foundation](01-foundation-shell-and-tooling.md)

## Completion

- Completed: 2026-07-16
- Commit: `5151e8f0dcaf505eead1ccdc67e022c8f475316d`

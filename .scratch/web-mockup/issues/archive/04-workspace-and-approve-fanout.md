# 04 — Workspace + approve fan-out

Status: completed
Type: task

## Parent

[PRD: Marketing OS web frontend — Milestone 1](../PRD.md)

## What to build

The campaign Workspace (`/campaigns/[slug]`) — the operator's surface for advancing one campaign — and the cross-screen "Approve" fan-out that is its payoff.

End-to-end behavior: the operator opens a campaign and sees an 8-stage stepper (Brief, Research, Strategy, Plan, Produce, Approve, Publish, Measure) marking each stage done / active / not-started. Selecting a stage shows its detail: what's done, what input it needs, and what happens after. The current (Strategy) stage shows a decision panel with **Approve**, **Request changes**, and (after approving) **Undo**. A right-hand panel has **Evidence** and **Comments** tabs — Evidence lists sources S1–S4 with type/title/note; "Request changes" switches the panel to Comments. An AI-assistant action rail (Generate alternatives, Challenge this assumption, Explain recommendation, Use stronger evidence, Rewrite for this audience, Check brand alignment) reveals each action's note, and "Check brand alignment" shows the brand scorecard instead.

The **fan-out**: approving Strategy flips the store's `approved` flag, which updates this Workspace (stage → Approved, later stages unlock per the prototype logic), the campaign's status/progress on the Campaigns table, and Home's pending-approvals stat + queue. Undo reverses it.

Use the prototype's `stageNames`, `stageStatus`, `stageDetails`, `aiDefs`/`aiNotes`, `scorecard`, and `evidence` data and logic verbatim.

## Acceptance criteria

- [x] Workspace renders the 8-stage stepper with correct done/active/not-started state; selecting a stage shows its detail (done / inputs / after).
- [x] Decision panel shows Approve + Request changes on the current stage; after approving, Undo is available.
- [x] Evidence/Comments tabs work; Evidence lists the source list; "Request changes" switches to Comments.
- [x] AI action rail toggles each action's note; "Check brand alignment" shows the scorecard.
- [x] Approving Strategy updates the Workspace stage state **and** the campaign's status on the Campaigns table **and** Home's pending-approvals count/queue; Undo reverses all three.
- [x] A Playwright smoke test drives approve-in-Workspace and asserts the Home pending-approvals count changed.
- [x] typecheck / lint / Prettier pass.

## Blocked by

- [03 — Campaigns table](03-campaigns-table.md)

## Comments

- Demo limitation (matches prototype semantics): every fixture campaign's workspace renders the Fernway demo stage content, and the Strategy decision panel flips the single global `approved` flag regardless of which campaign's workspace it is opened from. Resolved at engine-wiring time (ADR-0012 open item).

## Completion

- Completed: 2026-07-16
- Commit: `5151e8f0dcaf505eead1ccdc67e022c8f475316d`

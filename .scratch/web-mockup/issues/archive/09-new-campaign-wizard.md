# 09 — New-campaign wizard → Campaigns/Workspace

Status: completed
Type: task

## Parent

[PRD: Marketing OS web frontend — Milestone 1](../PRD.md) · flows: `development/new-campaign-flow.md`

## What to build

A multi-step new-campaign wizard (`/campaigns/new`), designed in the mockup's visual language, that collects the **minimum-required** campaign inputs and, on completion, creates a campaign that appears in the Campaigns table and opens its Workspace at the Brief stage.

End-to-end behavior: from the Campaigns "New campaign" button, the operator runs a wizard covering the minimum-required inputs from `development/new-campaign-flow.md` — Campaign request, Business objective, Target audience, Offer & conversion, Budget & timeline, Channels — with forward/back navigation and a review step summarizing inputs before creating. Where audiences overlap onboarding, the operator selects from existing audience segments rather than retyping. Validation enforces the "minimum required campaign inputs." Creating the campaign appends a row to the Campaigns table (in the store) and navigates to its Workspace, which opens at the **Brief** stage rendered from the entered brief. Deeper stages keep the Fernway demo content (documented limitation).

Cover minimum-required fields only.

## Acceptance criteria

- [x] Wizard renders as multi-step (request → objective → audience → offer/budget/timeline → channels → review) in the mockup's design language.
- [x] Audience step lets the operator select from existing audience segments.
- [x] Validation enforces the minimum-required inputs before the review/create step.
- [x] Creating the campaign adds a row to the Campaigns table and opens its Workspace at the Brief stage showing the entered data.
- [x] A Playwright smoke test drives the wizard to completion and asserts the new campaign appears in the table and its Workspace opens at Brief.
- [x] typecheck / lint / Prettier pass.

## Blocked by

- [03 — Campaigns table](03-campaigns-table.md)
- [04 — Workspace + approve fan-out](04-workspace-and-approve-fanout.md)

## Comments

- Created campaigns open at Brief rendered from entered data; stages beyond Brief keep the Fernway demo content per the PRD's documented limitation.

## Completion

- Completed: 2026-07-16
- Commit: `5151e8f0dcaf505eead1ccdc67e022c8f475316d`

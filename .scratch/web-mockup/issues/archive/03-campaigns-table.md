# 03 — Campaigns table

Status: completed
Type: task

## Parent

[PRD: Marketing OS web frontend — Milestone 1](../PRD.md)

## What to build

The Campaigns portfolio screen: a table of every campaign rendered from fixtures, and the entry points into the Workspace and the new-campaign wizard.

End-to-end behavior: the operator opens Campaigns and sees a table with name, objective, current stage (e.g. `3/8`), a status pill, the next action, and last-updated. Clicking a row opens that campaign's Workspace (`/campaigns/[slug]`). A "New campaign" button is present and routes to `/campaigns/new` (the wizard is inert until slice 09 — the button navigating to the stub is enough here).

Use the prototype's `campaignRows` data. Status pills reuse the StatusPill primitive from slice 02.

## Acceptance criteria

- [x] Campaigns table renders all fixture rows with name, objective, stage X/8, status pill, next action, updated.
- [x] Clicking a row navigates to that campaign's Workspace route.
- [x] "New campaign" button navigates to `/campaigns/new`.
- [x] Status pills use the shared StatusPill / canonical taxonomy.
- [x] A Playwright smoke test asserts the table renders and a row click lands on the Workspace route.
- [x] typecheck / lint / Prettier pass.

## Blocked by

- [02 — Home screen + shared primitives](02-home-screen-and-primitives.md)

## Completion

- Completed: 2026-07-16
- Commit: `5151e8f0dcaf505eead1ccdc67e022c8f475316d`

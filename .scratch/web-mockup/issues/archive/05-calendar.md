# 05 — Calendar

Status: completed
Type: task

## Parent

[PRD: Marketing OS web frontend — Milestone 1](../PRD.md)

## What to build

The Calendar screen with its three view modes and item-detail panel, rendered from fixtures.

End-to-end behavior: the operator opens Calendar and can toggle between **month grid**, **list**, and **by-campaign** modes. The month grid shows each day's content items colored by status with today highlighted. Selecting an item opens its detail: campaign, audience, funnel objective, channel, content pillar, scheduled date, and performance (if published). List mode shows every item with its metadata columns and status; by-campaign mode groups items under their campaign with counts.

Use the prototype's `calItems()` data and the `calMode` / `calSelIdx` store fields. Status uses the shared StatusPill / taxonomy.

## Acceptance criteria

- [x] Mode toggle switches between grid, list, and by-campaign; the active mode is indicated.
- [x] Month grid places items on the correct days, colors them by status, and highlights today.
- [x] Selecting an item shows its full detail (campaign, audience, funnel, channel, pillar, scheduled date, perf if any).
- [x] List mode shows all items with metadata + status; by-campaign mode groups with counts.
- [x] A Playwright smoke test asserts the mode toggle works and selecting an item shows its detail.
- [x] typecheck / lint / Prettier pass.

## Blocked by

- [02 — Home screen + shared primitives](02-home-screen-and-primitives.md)

## Completion

- Completed: 2026-07-16
- Commit: `5151e8f0dcaf505eead1ccdc67e022c8f475316d`

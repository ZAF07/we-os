# 07 — Performance

Status: completed
Type: task

## Parent

[PRD: Marketing OS web frontend — Milestone 1](../PRD.md)

## What to build

The Performance screen: headline metrics with deltas and the three narrative sections, rendered from fixtures.

End-to-end behavior: the operator opens Performance and sees headline metrics (Reach, Engaged CTR, New subscriptions, CAC) each with a delta vs. prior, followed by a "why this is happening" section (the drivers), a "what to change" section (concrete recommendations), and a "what's working — keep" section.

Use the prototype's `perfBig`, `perfWhy`, `perfChange`, and `perfKeep` data. Reuse the StatCard primitive from slice 02.

## Acceptance criteria

- [x] Headline metrics render with values and deltas (delta direction/color per fixtures).
- [x] Why / what-to-change / what's-working sections render from fixtures.
- [x] A Playwright smoke test asserts the metrics and the three sections render.
- [x] typecheck / lint / Prettier pass.

## Blocked by

- [02 — Home screen + shared primitives](02-home-screen-and-primitives.md)

## Completion

- Completed: 2026-07-16
- Commit: `5151e8f0dcaf505eead1ccdc67e022c8f475316d`

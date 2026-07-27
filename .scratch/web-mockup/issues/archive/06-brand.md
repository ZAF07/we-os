# 06 — Brand

Status: completed
Type: task

## Parent

[PRD: Marketing OS web frontend — Milestone 1](../PRD.md)

## What to build

The Brand screen: a navigable index of the nine brand sections with their entries, rendered from fixtures, and the deep-link target for Home's flagged-claim CTAs.

End-to-end behavior: the operator opens Brand and sees a left index (Positioning, Products & services, Audience segments, Voice & tone, Claims & evidence, Visual identity, Restricted language, Competitors, Approved examples). Selecting a section shows its entries, each with a "verified" date and any warnings (Restricted language) or notes (e.g. a pending claim "blocking 1 asset"). Home's flagged-claim CTA (slice 02) deep-links to the exact section (via the `brandIdx` store field).

Use the prototype's `brandSections` data verbatim.

## Acceptance criteria

- [x] Brand renders the 9-section index; selecting a section shows its entries.
- [x] Entries show verified dates; Restricted-language entries render as warnings; pending-claim notes (e.g. "blocking 1 asset") are shown.
- [x] Navigating from Home's flagged-claim CTA lands on the correct Brand section.
- [x] A Playwright smoke test asserts section navigation and that a deep-link opens the right section.
- [x] typecheck / lint / Prettier pass.

## Blocked by

- [02 — Home screen + shared primitives](02-home-screen-and-primitives.md)

## Completion

- Completed: 2026-07-16
- Commit: `5151e8f0dcaf505eead1ccdc67e022c8f475316d`

# 08 — Onboarding wizard → Brand

Status: completed
Type: task

## Parent

[PRD: Marketing OS web frontend — Milestone 1](../PRD.md) · flows: `development/onboarding-flow.md`

## What to build

A multi-step onboarding wizard, designed in the mockup's visual language (same shell, tokens, primitives), that collects the **core** durable company context and, on completion, populates the Brand screen.

End-to-end behavior: a new customer runs the wizard through steps covering the core / minimum-required fields from `development/onboarding-flow.md` — Business profile, Customer understanding, Positioning, Brand & voice, Compliance (restricted claims/terminology) — with a visible progress indicator and forward/back navigation. Required fields are validated before advancing. **No AI extraction** (manual entry; the wizard should reflect that expectation). Completing the wizard writes into the Brand data structure in the store so the entered positioning, audiences, voice, and restricted language appear on the Brand screen.

Cover core fields only — not every field in the flow doc. Reuse existing form primitives / shadcn inputs re-themed to the design.

## Acceptance criteria

- [x] Wizard renders as multi-step with a progress indicator and forward/back navigation, in the mockup's design language.
- [x] Required-field validation blocks advancing past an incomplete step.
- [x] Steps cover the core company/customer/positioning/brand/compliance fields (not the exhaustive list); no AI-extraction step.
- [x] Completing the wizard updates the store so the entered data is visible on the Brand screen.
- [x] A Playwright smoke test drives the wizard to completion and asserts the entered data shows on Brand.
- [x] typecheck / lint / Prettier pass.

## Blocked by

- [06 — Brand](06-brand.md)

## Completion

- Completed: 2026-07-16
- Commit: `5151e8f0dcaf505eead1ccdc67e022c8f475316d`

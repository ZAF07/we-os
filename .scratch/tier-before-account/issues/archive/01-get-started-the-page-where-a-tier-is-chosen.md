# 01 — Get Started, the page where a tier is chosen

Status: completed
Type: task

## Parent

[PRD: A tier before an account](../PRD.md) · [ADR-0027](../../../docs/adr/0027-the-platform-creates-the-tenant-and-owns-the-tier.md)

## What to build

A visitor who wants to try We-OS is asked which **Tier** before they are asked for an email.

A new public page, **Get Started**, in the public route group and the proxy's public matcher. It composes the *existing* tier-card and FAQ components — it does not restate a tier, a price, a credit amount, or an answer. Its own content is a heading and an intro that ask for the decision rather than explain the pricing, replacing Pricing's "The whole product, on every tier." It has no final-call section: the page is the call.

Every generic "Get started" button on the public half — top bar, hero, final call — leads here instead of to sign-up. Their label stays "Get started", so the button and the page it opens agree.

The tier cards' button label changes from "Get started" to **Launch**, in the one component that renders a tier, so Pricing and Get Started cannot disagree. Launch is the action that will one day open checkout; today it opens sign-up carrying the chosen tier. Pricing's tier buttons keep the destination they have — someone who decided on Pricing has already made the choice this page exists to extract.

Copy follows the landing feature's voice rules unchanged: no first-person "we", no trial, refund or cancellation promise, nothing the product cannot honour today.

Nothing is hardcoded that already exists: the tiers, their prices, their credits, the recommended tier and the sign-up address all come from the tier module, and the questions come from the FAQ component. This page introduces no second copy of any of them.

## Acceptance criteria

- [x] With no session, Get Started returns 200 and shows the three tiers with the same names, prices and credits as Pricing, rendered by the same component.
- [x] Its heading asks for the decision and is not Pricing's heading; the FAQ is present; no final-call section appears.
- [x] Every tier button on both Get Started and Pricing reads "Launch", and each carries its own tier to sign-up.
- [x] The top bar, hero and final-call "Get started" buttons lead to Get Started; their label is unchanged.
- [x] Pricing's tier buttons keep their existing destinations.
- [x] The page adds no second definition of a tier name, price, credit amount or FAQ answer.
- [x] The existing visitor assertions — voice rules, and phone width without horizontal scroll — pass on Get Started as they do on the Landing and Pricing.
- [x] The page makes no engine call.
- [x] TypeScript, ESLint, Prettier, vitest and the Playwright suite pass, and the page is confirmed in the running app.

## Blocked by

None - can start immediately.

## Completion

- Completed: 2026-09-09
- Commits:
  - `9b8d758` Get Started: the page where a tier is chosen before an account exists
  - `8cc55e2` Address code review: one set-once judgement, honest docstrings, real assertions (the intro copy)
  - merged to main as `b6c878f` Merge: a tier is chosen before an account exists, and the platform creates the tenant

### Evidence

- **Criterion 1** — `web/src/app/(public)/get-started/page.tsx` composes `TierCards` and `Faq`, the same components Pricing renders. `web/tests/public.spec.ts` "Get Started shows the same tiers as Pricing, asks for the decision, and is the call" opens `/get-started` with no session, asserts status 200 and each tier's name, price and credits.
- **Criterion 2** — The heading is "Choose your tier." (`page.tsx`, an `h1`), asserted by the same spec alongside `#faq` being visible, `#start` having no match, and Pricing's "The whole product, on every tier." being absent.
- **Criterion 3** — `web/src/components/public/tier-card.tsx` renders one `Launch` link per tier; the Pricing and Get Started specs assert the label and the `/sign-up?tier=<name>` address for all three tiers.
- **Criterion 4** — `top-bar.tsx`, `hero.tsx` and `final-call.tsx` link "Get started" to `/get-started`; "every generic Get started button leads to Get Started, not to sign-up" asserts every such link on `/` and `/pricing`.
- **Criterion 5** — `TierCards` defaults its destination to `signUpHref`, and Pricing passes nothing; "Pricing shows the three tiers, each launching sign-up with the tier remembered" asserts the unchanged addresses.
- **Criterion 6** — The page defines no tier, price, credit or answer: its only copy is the eyebrow, heading and intro. Names, prices and credits come from `web/src/lib/tiers.ts` through `TierCards`; the questions from `Faq`.
- **Criterion 7** — "the copy keeps the voice" and "the public pages stack at a phone width without horizontal scroll" iterate over `/`, `/pricing` and `/get-started`; "the FAQ answers the same five questions" does too. Screenshots at 1280 and 375 px checked by eye.
- **Criterion 8** — The page imports nothing from `@/lib/engine`; it reads only the Clerk session (issue 03) to resolve where Launch leads.
- **Criterion 9** — `tsc --noEmit`, `eslint`, `prettier --check` and `vitest run` (80 tests) pass; the full Playwright suite on the final code passed 64 with 6 skipped (the tenantless project, which waits on a provisioned user) against a freshly seeded compose stack. `/get-started` returned 200 in the running app and was checked at both widths.

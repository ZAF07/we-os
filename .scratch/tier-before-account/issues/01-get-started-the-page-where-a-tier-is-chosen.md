# 01 — Get Started, the page where a tier is chosen

Status: ready-for-agent
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

- [ ] With no session, Get Started returns 200 and shows the three tiers with the same names, prices and credits as Pricing, rendered by the same component.
- [ ] Its heading asks for the decision and is not Pricing's heading; the FAQ is present; no final-call section appears.
- [ ] Every tier button on both Get Started and Pricing reads "Launch", and each carries its own tier to sign-up.
- [ ] The top bar, hero and final-call "Get started" buttons lead to Get Started; their label is unchanged.
- [ ] Pricing's tier buttons keep their existing destinations.
- [ ] The page adds no second definition of a tier name, price, credit amount or FAQ answer.
- [ ] The existing visitor assertions — voice rules, and phone width without horizontal scroll — pass on Get Started as they do on the Landing and Pricing.
- [ ] The page makes no engine call.
- [ ] TypeScript, ESLint, Prettier, vitest and the Playwright suite pass, and the page is confirmed in the running app.

## Blocked by

None - can start immediately.

# 02 — Tiers, defined once, shown on Pricing and on the Landing

Status: ready-for-agent
Type: task

## Parent

[PRD: We-OS Landing and Pricing](../PRD.md) · [ADR-0020](../../../docs/adr/0020-usage-ledger-and-enforced-quota.md) (2026-09-08 amendment)

## What to build

A visitor can compare the three **Tiers** and reach sign-up with their choice remembered.

One pure module holds the tiers: name, monthly price in USD, monthly credits, a one-line audience, and whether the tier is highlighted. Placeholder values: Operator 59 / 6,000 ("For one business finding its footing"), Strategist 89 / 10,000 ("For a business running campaigns every month", highlighted as the common choice), Command 115 / 20,000 ("For a business that never stops marketing"). The same module builds the sign-up address for a tier by adding a `tier` query parameter with the lowercase tier name. Nothing reads that parameter yet. When real pricing is decided, this module is the only place that changes.

One tier card component renders a tier: name, price per month, credits per month, audience line, a short "everything included" line, and a "Get started" button linking to the tier's sign-up address. Every tier includes the whole product; they differ only in credits, and the cards say so.

A `/pricing` page under the public layout shows a short heading, a one-line explanation of credits (what the business spends on generation, granted monthly), and the three cards. The Landing gains a "Pricing" section using the same cards. The top bar and footer gain a "Pricing" link.

Copy follows the PRD voice: warm, plain, no "we", no trial, refund, or cancellation promises.

Testing: a unit test for the tier module (three tiers in order, Strategist highlighted, sign-up address per tier). Visitor Playwright spec: `/pricing` returns 200 and shows the three names, prices, and credits; each tier button links to sign-up with its tier parameter; the Landing's pricing section shows the same three tiers.

## Acceptance criteria

- [ ] The tiers and the sign-up address builder live in one pure module with a passing unit test.
- [ ] With no session, `/pricing` returns 200 and shows Operator, Strategist, and Command with USD 59, 89, 115 per month and 6,000, 10,000, 20,000 credits.
- [ ] Strategist is visibly marked as the common choice.
- [ ] Each tier's button links to sign-up with `tier=operator`, `tier=strategist`, or `tier=command`.
- [ ] The Landing shows the same three cards from the same component, and "Pricing" links appear in the top bar and footer.
- [ ] The page states that every tier includes the whole product and differs only in credits, and makes no trial, refund, or cancellation claim.
- [ ] `pnpm typecheck`, `pnpm lint`, `pnpm format:check`, `pnpm test:unit`, and `pnpm test` pass, and the change is checked in the running app.

## Blocked by

- [01 — Split the app into public and signed-in halves, with a bare Landing](01-split-public-and-app-halves-with-bare-landing.md)

# 02 — Tiers, defined once, shown on Pricing and on the Landing

Status: completed
Type: task

## Parent

[PRD: We-OS Landing and Pricing](../../archive/PRD.md) · [ADR-0020](../../../../docs/adr/0020-usage-ledger-and-enforced-quota.md) (2026-09-08 amendment)

## What to build

A visitor can compare the three **Tiers** and reach sign-up with their choice remembered.

One pure module holds the tiers: name, monthly price in USD, monthly credits, a one-line audience, and whether the tier is highlighted. Placeholder values: Operator 59 / 6,000 ("For one business finding its footing"), Strategist 89 / 10,000 ("For a business running campaigns every month", highlighted as the common choice), Command 115 / 20,000 ("For a business that never stops marketing"). The same module builds the sign-up address for a tier by adding a `tier` query parameter with the lowercase tier name. Nothing reads that parameter yet. When real pricing is decided, this module is the only place that changes.

One tier card component renders a tier: name, price per month, credits per month, audience line, a short "everything included" line, and a "Get started" button linking to the tier's sign-up address. Every tier includes the whole product; they differ only in credits, and the cards say so.

A `/pricing` page under the public layout shows a short heading, a one-line explanation of credits (what the business spends on generation, granted monthly), and the three cards. The Landing gains a "Pricing" section using the same cards. The top bar and footer gain a "Pricing" link.

Copy follows the PRD voice: warm, plain, no "we", no trial, refund, or cancellation promises.

Testing: a unit test for the tier module (three tiers in order, Strategist highlighted, sign-up address per tier). Visitor Playwright spec: `/pricing` returns 200 and shows the three names, prices, and credits; each tier button links to sign-up with its tier parameter; the Landing's pricing section shows the same three tiers.

## Acceptance criteria

- [x] The tiers and the sign-up address builder live in one pure module with a passing unit test.
- [x] With no session, `/pricing` returns 200 and shows Operator, Strategist, and Command with USD 59, 89, 115 per month and 6,000, 10,000, 20,000 credits.
- [x] Strategist is visibly marked as the common choice.
- [x] Each tier's button links to sign-up with `tier=operator`, `tier=strategist`, or `tier=command`.
- [x] The Landing shows the same three cards from the same component, and "Pricing" links appear in the top bar and footer.
- [x] The page states that every tier includes the whole product and differs only in credits, and makes no trial, refund, or cancellation claim.
- [x] `pnpm typecheck`, `pnpm lint`, `pnpm format:check`, `pnpm test:unit`, and `pnpm test` pass, and the change is checked in the running app.

## Blocked by

- [01 — Split the app into public and signed-in halves, with a bare Landing](01-split-public-and-app-halves-with-bare-landing.md)

## Completion

- Completed: 2026-09-08
- Commits:
  - `c9927b4` Tiers, defined once, shown on Pricing and on the Landing
  - `fc5d251` Address code review: vocabulary, one pricing intro, one height token, no animation
  - merged to main as `00c13af` Merge: We-OS Landing and Pricing, the public half of the app

### Evidence

- **Criterion 1** — `web/src/lib/tiers.ts` exports `TIERS` (name, `monthlyPriceUsd`, `monthlyCredits`, `suits`, `highlighted`) and `signUpHref`. `web/src/lib/tiers.test.ts` (three tests: order, Strategist and only Strategist highlighted, the three sign-up addresses) was red with the module missing and green once it existed. The field is `suits` rather than "audience" because the glossary reserves that word for an Audience Segment.
- **Criterion 2** — `web/tests/public.spec.ts` "Pricing shows the three tiers, each linking to sign-up with the tier remembered": status 200 at `/pricing`, and within each tier's article `$59`/`$89`/`$115` and `6,000`/`10,000`/`20,000`.
- **Criterion 3** — the Strategist card alone carries a "Recommended" badge (`web/src/components/public/tier-card.tsx`); the spec asserts it on Strategist and absent on Operator. Code review changed the label from the mockup's "Most chosen": a recommendation is the product's to make, while popularity would be a claim about other businesses that nothing backs yet.
- **Criterion 4** — the same spec asserts each card's "Get started" link is `/sign-up?tier=operator`, `…=strategist`, `…=command`, on Pricing and on the Landing. Nothing reads the parameter (`sign-up` page docstring).
- **Criterion 5** — `TierCards` is rendered by `web/src/components/public/pricing-section.tsx` (Landing, `#pricing`) and `web/src/app/(public)/pricing/page.tsx`; "the Landing shows the same three tiers, and Pricing is one link away" asserts the three cards under `#pricing` and a `Pricing` link with `href="/pricing"` in both the banner and the footer. The top bar's links are hidden below the tablet breakpoint, as in the mockup; the footer link remains on a phone.
- **Criterion 6** — the cards' footnote reads "Prices in USD. Every tier includes the whole product and differs only in credits." and each card says "Everything included: every stage, every specialist, your full Brand DNA." The voice spec scans both pages for `free trial|refund|cancel anytime|money back|testimonial` and finds none. Known tension, kept as the issue prescribes: the copy says credits are granted each month, while the engine has no monthly reset yet and billing is out of scope.
- **Criterion 7** — `pnpm typecheck`, `pnpm lint`, `pnpm format:check` and `pnpm test:unit` (8 files, 72 tests) pass. `pnpm test` was run against a freshly started e2e stack (`make e2e-up`, then `E2E_STACK=compose pnpm test`): **60 passed, 0 failed** across the `setup`, `chromium`, `chromium-onboarding` and `chromium-public` projects, on the final code (`b78329f`). On a stack that had already absorbed five suite runs, the campaign-creating specs failed in the way [e2e-suite-flake 01](../../../e2e-suite-flake/issues/01-campaign-creating-specs-fail-under-parallel-workers.md) documents; a note with today's numbers was added there. Checked in the running app: full-page screenshots of `/`, `/pricing` and `/sign-in` at 1280px and 375px.

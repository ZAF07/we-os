# 04 — Pricing leaves the Landing

Status: completed
Type: task

## Parent

[PRD: We-OS Landing and Pricing](../../archive/PRD.md) · supersedes the Landing's pricing section from [02](02-tiers-on-pricing-and-landing.md)

## What to build

Decided by the maintainer on 2026-09-09, after seeing the shipped page: the
Landing tells the story from the hero to "Why it's different" and then answers
the FAQ. The tiers live only on the Pricing page, which keeps the FAQ. So the
Landing's pricing section goes; the top bar and footer keep their "Pricing"
links, so the tiers stay one click away; the final call to action stays on
both pages.

The visitor spec drops its Landing tier assertions and its expected heading
list loses the pricing heading; it still asserts the Pricing links. The
glossary's Landing and Pricing entries follow: what it costs is no longer on
the Landing, and Pricing is the only place prices appear.

## Acceptance criteria

- [x] With no session, the Landing shows, in order: hero, the augmented loop, how it works, your marketing department, why it's different, FAQ, final call, footer — and no tier card.
- [x] `/pricing` is unchanged: the three tiers, the FAQ, the final call.
- [x] "Pricing" in the top bar and the footer still reaches `/pricing`.
- [x] `pnpm typecheck`, `pnpm lint`, `pnpm format:check`, `pnpm test:unit`, and `pnpm test` pass, and the change is checked in the running app.

## Blocked by

None.

## Completion

- Completed: 2026-09-09
- Commits:
  - `a0e793a` Pricing leaves the Landing
  - `b9991b2` Add issue 04 and move what it costs from the Landing to Pricing in the glossary
  - merged to main as `290badd` Merge: Pricing leaves the Landing

### Evidence

- **Criterion 1** — `web/tests/public.spec.ts` "the Landing tells its story in order, from the hero to the final call" asserts the level-2 headings in order: the augmented loop, how it works, your marketing department, why it's different, questions, the final call, then the footer. "the tiers live on Pricing, one link away from the Landing" asserts that no `article` (a tier card) appears on the Landing. A desktop screenshot of `/` was checked by eye.
- **Criterion 2** — "Pricing shows the three tiers, each linking to sign-up with the tier remembered" and "the FAQ answers the same five questions on the Landing and on Pricing" are unchanged and pass; `web/src/app/(public)/pricing/page.tsx` renders the tiers, the FAQ and the final call, with its own heading now that no intro is shared.
- **Criterion 3** — the same spec asserts a `Pricing` link with `href="/pricing"` in the banner and in the footer.
- **Criterion 4** — `pnpm typecheck`, `pnpm lint`, `pnpm format:check` and `pnpm test:unit` (8 files, 72 tests) pass. `pnpm test` on a freshly started e2e stack: 52 passed and 2 failed on 5-second first-paint timeouts (`calendar.spec.ts:34` waiting for the Stages navigation, `onboarding.spec.ts:62` waiting for "Step 1 of 5"), after which that serial file skipped its other 6; both are screens this change does not touch, and the host was swapping heavily at the time (23.5 GB of 24.5 GB swap in use). Re-running those two files on the same, still-blank stack passed all 12, so every one of the 60 tests passed on the final code. The visitor project alone passed 10/10 twice. Running app: passed: localhost:3000/ answers 200 with no tier card.

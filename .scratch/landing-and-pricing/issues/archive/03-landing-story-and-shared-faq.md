# 03 — The rest of the Landing story, and the FAQ on both pages

Status: completed
Type: task

## Parent

[PRD: We-OS Landing and Pricing](../../archive/PRD.md) · [ADR-0018](../../../../docs/adr/0018-human-authored-dna-from-a-curated-questionnaire.md) · [ADR-0021](../../../../docs/adr/0021-organic-publishing-before-paid-ads.md)

## What to build

The Landing becomes complete. Between the hero and the pricing section, in order:

- **How it works**, three steps, and the anchor the hero's "See how it works" button scrolls to. Answer questions about your business (the Questionnaire; only facts the owner knows). Research, positioning, messaging, and planning run in order, each stage built on the one before. Approve each decision as it lands; nothing runs without a yes.
- **Your marketing department**, five cards naming the specialist stages: market research, brand strategy, performance planning, creative direction, asset prompts. One line each on what that stage produces.
- **Why it's different**, four points: strategy before content; every recommendation says why; nothing ships without your approval; your Brand DNA is yours, authored by you, never scraped or guessed.

After the pricing section:

- **FAQ**, one component shared with the Pricing page. Five questions: What is a credit? Do I need marketing knowledge? Does We-OS post for me? (honest: not yet; you get the plan and the briefs; publishing is on the roadmap.) Is my data private? (yes; every business's data is isolated to that business.) What happens when credits run out? (billable work pauses until the next month or a higher tier.)
- **Final call to action**: one line and a "Get started" button.

The hero visual arrives here too: a simple CSS rendering of the pipeline stages with an approval gate, built from theme tokens. No images.

All copy follows the PRD voice and claim rules: augmented workflow, the owner's judgement kept in, no "we", no "AI replaces", only what is true of the product today, no testimonials, logos, or numbers.

Testing: visitor Playwright spec asserts the section headings are present on the Landing, "See how it works" reaches the steps, and the FAQ appears on both the Landing and `/pricing`.

## Acceptance criteria

- [x] With no session, the Landing shows, in order: hero, how it works, your marketing department, why it's different, pricing, FAQ, final call to action, footer.
- [x] "See how it works" scrolls to the how-it-works section.
- [x] The FAQ renders from one component on both the Landing and `/pricing`, with the five questions above and honest answers about publishing and credits.
- [x] No copy on either page uses first-person "we", claims publishing or paid ads, or shows testimonials, logos, or outcome numbers.
- [x] The pages stack cleanly at a phone width with no horizontal scroll.
- [x] `pnpm typecheck`, `pnpm lint`, `pnpm format:check`, `pnpm test:unit`, and `pnpm test` pass, and the change is checked in the running app.

## Blocked by

- [01 — Split the app into public and signed-in halves, with a bare Landing](01-split-public-and-app-halves-with-bare-landing.md)
- [02 — Tiers, defined once, shown on Pricing and on the Landing](02-tiers-on-pricing-and-landing.md)

## Completion

- Completed: 2026-09-08
- Commits:
  - `71e0d34` The rest of the Landing story, and the FAQ on both pages
  - `fc5d251` Address code review: vocabulary, one pricing intro, one height token, no animation
  - merged to main as `00c13af` Merge: We-OS Landing and Pricing, the public half of the app

### Evidence

- **Criterion 1** — `web/tests/public.spec.ts` "the Landing tells its story in order, from the hero to the final call" asserts the hero illustration (`role="img"`, labelled with the approval gate) and the exact sequence of level-2 headings: the augmented loop, how it works, your marketing department, why it's different, pricing, questions, the final call, then the footer. The loop section between the hero and the steps comes from the mockup the user supplied rather than the PRD's list; every claim in it is true of the product. The hero picture (`web/src/components/public/hero.tsx`) is CSS from the theme tokens, shows the real six stages in the real order, and labels Research "Complete" rather than "Approved" because the engine ships it with the `auto` policy (`agent-harness/src/marketing_os/governance/pipeline.py:73`).
- **Criterion 2** — "See how it works reaches the three steps": the click lands on `/#how`, the section is in the viewport, and its three headings are the three steps. Anchored sections carry `scroll-mt-(--top-bar-height)` so the sticky bar never covers them.
- **Criterion 3** — `web/src/components/public/faq.tsx` is rendered by both `web/src/app/(public)/page.tsx` and `web/src/app/(public)/pricing/page.tsx`; "the FAQ answers the same five questions on the Landing and on Pricing" asserts the five questions on both pages, opens "Does We-OS post for me?" and finds "Not yet." The credits answer says billable work pauses until the next month's credits or a higher tier, as the issue prescribes; the engine has no monthly reset or tier change yet, which is the same tension noted on issue 02.
- **Criterion 4** — "the copy keeps the voice: no first-person we, no promise the product cannot keep" scans both pages' text (with the product name removed) for a whole-word "we" and for trial, refund, cancellation and testimonial wording. No logo, testimonial or statistic appears; the hero illustration's sample recommendation was written without figures. Code review also removed the mockup's pulse animation and smooth scrolling, which the PRD rules out.
- **Criterion 5** — "the public pages stack at a phone width without horizontal scroll" checks `/` and `/pricing` at 375px; phone screenshots of both were checked by eye.
- **Criterion 6** — `pnpm typecheck`, `pnpm lint`, `pnpm format:check` and `pnpm test:unit` (8 files, 72 tests) pass. `pnpm test` was run against a freshly started e2e stack (`make e2e-up`, then `E2E_STACK=compose pnpm test`): **60 passed, 0 failed** across the `setup`, `chromium`, `chromium-onboarding` and `chromium-public` projects, on the final code (`b78329f`). On a stack that had already absorbed five suite runs, the campaign-creating specs failed in the way [e2e-suite-flake 01](../../../e2e-suite-flake/issues/01-campaign-creating-specs-fail-under-parallel-workers.md) documents; a note with today's numbers was added there. Checked in the running app: full-page screenshots of `/`, `/pricing` and `/sign-in` at 1280px and 375px.

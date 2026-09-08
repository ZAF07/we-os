# 03 — The rest of the Landing story, and the FAQ on both pages

Status: ready-for-agent
Type: task

## Parent

[PRD: We-OS Landing and Pricing](../PRD.md) · [ADR-0018](../../../docs/adr/0018-human-authored-dna-from-a-curated-questionnaire.md) · [ADR-0021](../../../docs/adr/0021-organic-publishing-before-paid-ads.md)

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

- [ ] With no session, the Landing shows, in order: hero, how it works, your marketing department, why it's different, pricing, FAQ, final call to action, footer.
- [ ] "See how it works" scrolls to the how-it-works section.
- [ ] The FAQ renders from one component on both the Landing and `/pricing`, with the five questions above and honest answers about publishing and credits.
- [ ] No copy on either page uses first-person "we", claims publishing or paid ads, or shows testimonials, logos, or outcome numbers.
- [ ] The pages stack cleanly at a phone width with no horizontal scroll.
- [ ] `pnpm typecheck`, `pnpm lint`, `pnpm format:check`, `pnpm test:unit`, and `pnpm test` pass, and the change is checked in the running app.

## Blocked by

- [01 — Split the app into public and signed-in halves, with a bare Landing](01-split-public-and-app-halves-with-bare-landing.md)
- [02 — Tiers, defined once, shown on Pricing and on the Landing](02-tiers-on-pricing-and-landing.md)

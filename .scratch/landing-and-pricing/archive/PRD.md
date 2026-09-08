# PRD: We-OS Landing and Pricing — the public half of the app

Status: completed
Category: feature
Date: 2026-09-08

Governed by ADRs [0012](../../../docs/adr/0012-nextjs-frontend-and-bff-in-monolith.md) (and its 2026-09-08 amendment), [0013](../../../docs/adr/0013-multi-tenant-saas-with-dual-verified-jwt.md), [0018](../../../docs/adr/0018-human-authored-dna-from-a-curated-questionnaire.md), [0020](../../../docs/adr/0020-usage-ledger-and-enforced-quota.md) (and its 2026-09-08 amendment), [0021](../../../docs/adr/0021-organic-publishing-before-paid-ads.md). Vocabulary per [CONTEXT.md](../../../CONTEXT.md): **Landing**, **Home**, **Tenant**, **Brand DNA**, **Credits**, **Tier**.

## Problem Statement

Someone who hears about We-OS and opens its address sees a sign-in form and nothing else. There is no page that says what the product is, how it works, or what it costs. The only signed-out routes are the sign-in and sign-up forms; the root of the site is the signed-in Home, so a visitor is bounced to sign-in before they have any reason to sign up.

Underneath that, the app has no notion of a public half. Every route assumes a session, the app shell hides itself by matching a hardcoded list of paths, and the product is called two different names in different places ("Marketing OS" in the shell and browser title, "we-OS" on the sign-in pages).

The result: a business owner cannot discover We-OS, cannot compare tiers, and cannot decide to sign up from the product itself.

## Solution

The root of the site becomes the **Landing**: a single public page in the same visual language as the app (indigo on slate, Instrument Sans, rounded cards) that says what We-OS is in plain, warm language, walks through how the workflow runs, introduces the specialist stages, states what makes it different, shows the three tiers, answers the obvious questions, and offers one way in: sign up or sign in.

A second public page, **Pricing**, shows the same three tiers with the questions people ask before paying.

The app is split into its two natural halves. Public routes (Landing, Pricing, sign-in, sign-up) render without the app shell and without a session. Signed-in routes (Home, Campaigns, Calendar, Brand, Performance, Onboarding) keep the shell and keep requiring a session. Home moves from the root to its own address, and a signed-in person who opens the root is sent there. The public name is **We-OS** everywhere the public sees it.

The voice throughout is the one settled in the grilling: open, warm, modern, light, with authority. We-OS is an **augmented workflow** for digital marketing that keeps the person's judgement in the loop. Never "we do it for you", never "AI replaces your team".

## User Stories

### Visitor arriving

1. As a visitor, I want to open the site's address and see what We-OS is, so that I can decide whether it is for me without signing up.
2. As a visitor, I want the first screen to say in one line what the product does, so that I do not have to scroll to understand it.
3. As a visitor, I want a clear "Get started" button at the top and in the hero, so that I can sign up the moment I decide to.
4. As a visitor, I want a "Sign in" button next to it, so that I can get back in if I already have an account.
5. As a visitor, I want a "See how it works" link that takes me to the explanation, so that I can read before committing.
6. As a visitor, I want the page to work on my phone, so that I can read it wherever I heard about it.
7. As a visitor, I want the page to load without a session and without touching the engine, so that it is fast and never shows an engine error.

### Understanding the product

8. As a visitor, I want to see the workflow as three steps I can grasp at a glance (answer questions about the business; research, positioning, and planning run in order; approve each decision), so that I understand what I would actually be doing.
9. As a visitor, I want the copy to describe an augmented workflow with my judgement in it, so that I am not sold "AI does your marketing" and then surprised by approval gates.
10. As a visitor, I want to see the specialist stages named (research, brand strategy, performance planning, creative direction, asset prompts), so that I know what work the platform covers.
11. As a visitor, I want to read what makes We-OS different (strategy before content; every recommendation says why; nothing runs without approval; the Brand DNA is authored by me, never scraped), so that I can tell it apart from a content generator.
12. As a visitor, I want every claim on the page to be true of the product today, so that what I see after sign-up matches what I was promised.
13. As a visitor, I want no fake testimonials, logos, or made-up statistics, so that the page earns trust rather than spending it.

### Pricing and tiers

14. As a visitor, I want to see the three tiers side by side (Operator, Strategist, Command) with monthly price and monthly credits, so that I can compare them in seconds.
15. As a visitor, I want a one-line description of who each tier suits, so that I can pick without a feature matrix.
16. As a visitor, I want one tier marked as the common choice, so that I have a default if I am unsure.
17. As a visitor, I want to see that every tier includes the whole product and differs only in credits, so that I do not fear being locked out of features.
18. As a visitor, I want a short explanation of what a credit is, so that the numbers mean something.
19. As a visitor, I want a dedicated Pricing page reachable from the top bar and the footer, so that I can send it to a colleague.
20. As a visitor, I want the tiers on the Landing and on the Pricing page to be identical, so that I never see two different prices.
21. As a visitor, I want clicking a tier's button to take me to sign-up with that tier remembered in the address, so that my choice is not lost.
22. As a visitor, I want the pricing not to promise trials, refunds, or "cancel anytime" that the product cannot yet honour, so that I am not misled.

### Questions

23. As a visitor, I want a short FAQ (what is a credit; do I need marketing knowledge; does We-OS post for me; is my data private; what happens when credits run out), so that my last doubts are answered on the page.
24. As a visitor, I want the FAQ to be honest that publishing is not available yet, so that I sign up for what exists.

### Signing up and in

25. As a visitor, I want "Get started" to open the existing sign-up flow, so that creating an account is the same flow the app already trusts.
26. As a visitor, I want "Sign in" to open the existing sign-in flow, so that I can reach my Home.
27. As a new business owner, I want to land on Home after sign-up, so that the next step (onboarding) is in front of me.
28. As a returning business owner, I want to land on Home after sign-in, so that I see what needs me.

### The signed-in half

29. As a signed-in business owner, I want opening the root address to take me straight to Home, so that I never see the sales page once I am a tenant.
30. As a signed-in business owner, I want Home to keep everything it has today (decision queue, in-progress campaigns, credits card, portfolio), so that nothing I rely on moves or breaks.
31. As a signed-in business owner, I want the nav rail's Home link to point at Home's new address, so that navigation still works.
32. As a signed-in business owner, I want a signed-out request to any app route to be sent to sign-in and back again afterwards, so that a stale session costs me one click, not my place.
33. As a signed-in business owner, I want the app shell's logo and the browser tab to say We-OS, so that the product has one name.

### Maintainers

34. As a maintainer, I want the public and signed-in halves to be two route groups with their own layouts, so that a new page lands in the right half by where it is placed, not by editing a list of paths.
35. As a maintainer, I want the tiers defined once in a small pure module, so that when prices and credits are decided there is exactly one place to change.
36. As a maintainer, I want the tier-to-sign-up link built in that same module, so that the tier name on the address is never hand-typed in two places.
37. As a maintainer, I want the page copy to sit in the page components rather than in a content system, so that the feature stays small.
38. As a maintainer, I want the browser suite to cover the public pages as a visitor with no session, so that a future change that accidentally locks the Landing behind auth fails a test.
39. As a maintainer, I want the existing Home and smoke specs updated to Home's new address, so that the suite stays green and honest.

## Implementation Decisions

- **Two route groups.** The web app is split into a public group and an app group, the standard Next.js way to give two sets of routes two layouts. The public group's layout renders the page directly with a top bar and footer of its own. The app group's layout renders the existing app shell. The shell's hardcoded list of "bare" routes is deleted, since the folder structure now decides.
- **Routes.** Landing at the root. Pricing at `/pricing`. Sign-in and sign-up keep their addresses and move into the public group. Home moves to `/home`. All other signed-in routes keep their addresses and move into the app group unchanged.
- **Auth boundary.** The middleware's public matcher covers the root, pricing, sign-in, and sign-up. A signed-in session that requests the root is redirected to Home by the middleware. Everything else keeps today's behaviour: signed-out is redirected to sign-in with a return address. As before, this redirect is a convenience; the engine remains the security boundary (ADR-0013).
- **Post-auth destination.** Sign-in and sign-up fall back to Home after completion, via the Clerk fallback-redirect settings, so a new business owner sees Home (and from there onboarding) rather than the Landing.
- **Landing sections, in order.** Top bar (brand mark, "How it works", "Pricing", "Sign in", "Get started"). Hero. How it works (three steps). Your marketing department (five specialist cards). Why it's different (four points). Pricing (three tier cards). FAQ. Final call to action. Footer (brand mark, "Pricing", "Sign in", copyright). No images; the hero visual is a simple CSS rendering of the pipeline with an approval gate, built from the theme tokens.
- **Hero copy, locked.** Headline: "Strategy before content. Always." Subline: "Augmented workflow for digital marketing. Expert practice built in, your judgement kept in. Answer the questions only you can answer, review each decision as it lands, and approve what runs." Buttons: "Get started" (primary), "See how it works" (outline, scrolls to the steps).
- **Voice rules for all other copy.** No first-person "we". No "AI replaces" or "AI-generated". Short plain sentences. Warm and light, with authority. Describe from the owner's side or describe the workflow.
- **Claims allowed.** The full strategy pipeline, approval gates at each stage, a Brand DNA authored by the business, tenant-isolated data, credits per tier. **Claims forbidden.** Posting to any platform, paid ads, trials, refunds, cancellation terms, logos, testimonials, numeric outcomes.
- **Tiers, one module.** A pure module exports the three tiers (name, monthly price in USD, monthly credits, one-line audience, whether highlighted) and a function that builds the sign-up address for a tier by adding a `tier` query parameter with the lowercase tier name. Values today are placeholders: Operator 59 / 6,000, Strategist 89 / 10,000, Command 115 / 20,000. Strategist is highlighted. Nothing reads the `tier` parameter yet.
- **One tier card component** renders a tier and is used by both the Landing's pricing section and the Pricing page, so they cannot drift.
- **Pricing page** is the tier cards plus the FAQ plus the final call to action, under the same public layout.
- **Name.** "We-OS" replaces "Marketing OS" in the shell brand mark, the browser title and description, and the sign-in and sign-up page headings. The specialist names and glossary vocabulary are used as-is in copy.
- **Credits wording.** Every new string says "credits". Existing Home strings that say "Allowance" are changed to "Credits" in this feature since they are user-facing copy. The `allowance` identifier in code, API, and database is not renamed here.
- **Theme.** The public pages reuse the existing tokens and primitives (button, card) with no new colour, font, or spacing scale. Light theme only, as the app is today. Responsive by default with a stacked layout under the tablet breakpoint.
- **No engine calls** from the public pages. They are static server components.

## Testing Decisions

A good test here opens a page the way a person would and checks what they would see or where they end up. It does not inspect components, class names, or internal state.

- **Browser suite (Playwright), as a visitor.** One extra project in the Playwright config runs the public specs with no saved session. It checks: the root and Pricing return 200 and show their sections and the three tier names with prices and credits; the tier buttons link to sign-up with the tier parameter; "Sign in" and "Get started" reach the Clerk pages; opening Home without a session redirects to sign-in.
- **Browser suite, signed in.** In the existing signed-in project: opening the root lands on Home; the nav rail marks Home active at its new address. The existing smoke and Home specs are updated to Home's new address and to the We-OS brand mark and "Credits" label.
- **Unit (vitest).** One test file for the tier module: three tiers in order, Strategist highlighted, and the sign-up link builder producing the expected address for each tier. Prior art: the pure-module tests beside `home.ts` and `campaigns.ts`.
- **Gates.** TypeScript strict, ESLint, Prettier, vitest, and the Playwright suite all pass before the work is called done. Nothing else on the public pages is unit tested; they are presentational, per ADR-0012's gate.

## Out of Scope

- Billing, checkout, subscriptions, or any payment provider. The `tier` parameter is carried, not consumed.
- Deciding the real prices, credit amounts, or the cost-to-credit rate. The numbers are placeholders in one module.
- Renaming the `allowance` identifier across engine, API, database, and frontend code. Separate issue.
- Terms of service, privacy policy, cookie notice, or any legal page. The footer links to nothing that does not exist.
- A contact address, support link, blog, changelog, documentation site, or status page.
- Dark theme, animations beyond simple hover states, images, illustrations, or screenshots of the app.
- Analytics, SEO tooling beyond a sensible title and description, sitemaps, or Open Graph images.
- Localisation.
- Any change to onboarding, the Questionnaire, Home's data, or the engine.

## Further Notes

- The grilling that produced this PRD also changed the glossary intro to the augment framing, added **Landing**, **Home**, **Credits**, and **Tier** to `CONTEXT.md`, and appended dated amendments to ADR-0012 and ADR-0020. Read those first.
- "Marketing OS" survives only as a descriptor ("the marketing OS for small businesses" style phrasing is fine); it is not the product name.
- When the real tiers are decided, the expected change is the values in the tier module and possibly the FAQ answer about credits. Nothing else should need to move.

## Completion

- Completed: 2026-09-08
- Commits, on branch `landing-and-pricing`:
  - `ac6557e` Split the app into public and signed-in halves, with a bare Landing
  - `c9927b4` Tiers, defined once, shown on Pricing and on the Landing
  - `71e0d34` The rest of the Landing story, and the FAQ on both pages
  - `fc5d251` Address code review: vocabulary, one pricing intro, one height token, no animation
  - `b78329f` Document the public half in the web README and env example
  - merged to main as `00c13af` Merge: We-OS Landing and Pricing, the public half of the app
- Per-criterion evidence lives on the three archived issues in [issues/archive/](../issues/archive/).
- Where the shipped page departs from this document, on purpose: the user-supplied mockup's "augmented loop" section sits between the hero and "How it works"; the highlighted tier says "Recommended" rather than "Most chosen", since no data backs a popularity claim yet; the top bar's section links hide below the tablet breakpoint, as in the mockup, with the footer's "Pricing" link always present.
- Open tension for the author: the copy says credits are granted monthly and that a business can move to a higher tier, as issues 02 and 03 prescribe, while the engine has no monthly reset and billing is out of scope.
- 2026-09-09: the maintainer moved pricing off the Landing ([issue 04](../issues/archive/04-pricing-leaves-the-landing.md)). The Landing now ends with the FAQ and the final call, and Pricing is the only place the tiers appear.

# PRD: Marketing OS web frontend — Milestone 1 (build the mockup)

Status: completed
Category: feature
Date: 2026-07-16

Governed by [ADR-0012](../../docs/adr/0012-nextjs-frontend-and-bff-in-monolith.md). Design source: the "Cadence v2" wireframe (`/Users/zaffere/wireframes-design/Cadence v2 (standalone).html`). Flow requirements: `development/onboarding-flow.md`, `development/new-campaign-flow.md`.

## Problem Statement

The backend domain engine (the LangGraph pipeline + FastAPI in `agent-harness/`) is essentially complete, but there is **no user interface**. An operator cannot see their campaigns, approve a stage, browse the content calendar, review the brand, or read performance without dropping to the CLI/API. The user has an approved visual design (the "Cadence" mockup) and wants it built as the first frontend milestone — the design is locked; the underlying user flows and APIs are not yet determined.

## Solution

A single Next.js (App Router, TypeScript) application at `web/` in this monolith, carrying the frontend and its BFF, that **faithfully reproduces the approved mockup** as a running app. Milestone 1 is a **static clone driven entirely by mock fixtures** — no calls to the FastAPI engine. It reproduces the six designed screens (Home, Campaigns, Workspace, Calendar, Brand, Performance), extends the same visual language to two new wizards (onboarding and new-campaign creation), and preserves the prototype's cross-screen interactivity via a client store. Wiring the BFF to the engine is a later milestone.

From the operator's perspective: they open the app, land on Home with their pending approvals and active campaigns, drill into a campaign Workspace to advance and approve stages, browse scheduled content on the Calendar, review the brand system, read what performance is telling them — and can onboard a new company or spin up a new campaign through guided wizards, seeing the results appear across the app.

## User Stories

### Application shell & navigation

1. As an operator, I want a persistent left nav rail with Home, Campaigns, Calendar, Brand, and Performance, so that I can move between areas from anywhere.
2. As an operator, I want the active nav item highlighted (and Workspace to highlight Campaigns), so that I always know where I am.
3. As an operator, I want a badge on Home showing my pending-approval count, so that I can see outstanding decisions at a glance.
4. As an operator, I want each view to have its own URL, so that I can bookmark, deep-link, and use browser back/forward.
5. As an operator, I want the "Marketing OS" brand mark in the nav, so that the product identity is consistent.
6. As an operator on a small screen, I want the nav to collapse into a drawer and content to reflow, so that the app is usable below desktop width.

### Home

7. As an operator, I want stat cards (Pending approvals, Active campaigns, Scheduled this week, Blocked), so that I get the state of my marketing at a glance.
8. As an operator, I want a prioritized decision/approval queue with typed tags (Decision, Flagged, Needs input), item context, due labels, and a CTA, so that I know what needs me next and can jump straight to it.
9. As an operator, I want each queue item's CTA to navigate to the right place (Workspace, or the relevant Brand section for a flagged claim), so that acting on it is one click.
10. As an operator, I want a list of active campaigns with status pill, progress %, and stage note, so that I can track everything in flight.
11. As an operator, I want a "blocked" list with the reason and an action, so that I can unblock stalled work.
12. As an operator, I want upcoming calendar items, key research findings, headline performance stats, and recommendations surfaced on Home, so that the important signals come to me.

### Campaigns

13. As an operator, I want a table of campaigns showing name, objective, current stage (e.g. 3/8), status, next action, and last-updated, so that I can scan the whole portfolio.
14. As an operator, I want a status pill per campaign using the shared status taxonomy, so that state is visually consistent everywhere.
15. As an operator, I want to click a campaign row to open its Workspace, so that I can work on it.
16. As an operator, I want a "New campaign" action that launches the creation wizard, so that I can start a campaign from here.

### Workspace (campaign detail)

17. As an operator, I want an 8-step stage stepper (Brief, Research, Strategy, Plan, Produce, Approve, Publish, Measure) showing done/active/not-started, so that I can see the campaign's journey and where it is.
18. As an operator, I want to select any stage to view its detail, so that I can inspect any part of the campaign.
19. As an operator, I want each stage's detail to show what's done, what input it needs from me, and what happens after, so that I understand the decision in front of me.
20. As an operator, I want a decision panel on the current stage with Approve and Request changes, so that I can advance the campaign or send it back.
21. As an operator, I want approving the Strategy stage to visibly update the campaign's status and progress and my Home queue/stats, so that the system feels connected and my action has consequences.
22. As an operator, I want to undo an approval, so that I can correct a mis-click in the demo.
23. As an operator, I want an AI-assistant action rail (Generate alternatives, Challenge this assumption, Explain recommendation, Use stronger evidence, Rewrite for this audience, Check brand alignment), so that I can interrogate a recommendation.
24. As an operator, I want selecting an AI action to reveal its response note (or the brand scorecard for "Check brand alignment"), so that I get useful assistance in context.
25. As an operator, I want a right-hand panel with Evidence and Comments tabs, the Evidence tab listing sources (S1–S4) with type/title/note, so that every recommendation traces to evidence.
26. As an operator, I want "Request changes" to switch the right panel to Comments, so that sending work back has a place to say why.

### Calendar

27. As an operator, I want three calendar modes — month grid, list, and by-campaign — with a toggle, so that I can view scheduled content the way that suits the task.
28. As an operator, I want the month grid to show each day's content items colored by status with today highlighted, so that I can see the publishing rhythm.
29. As an operator, I want to select a content item and see its full detail (campaign, audience, funnel objective, channel, content pillar, scheduled date, and performance if published), so that I understand each piece of work.
30. As an operator, I want the list mode to show every item with its metadata columns and status, so that I can scan everything linearly.
31. As an operator, I want the by-campaign mode to group items under their campaign with counts, so that I can review a single campaign's schedule.

### Brand

32. As an operator, I want a left index of brand sections (Positioning, Products & services, Audience segments, Voice & tone, Claims & evidence, Visual identity, Restricted language, Competitors, Approved examples), so that I can navigate the brand system.
33. As an operator, I want each section to show its entries with a "verified" date and any warnings/notes, so that I know what's current and what's risky.
34. As an operator, I want Restricted language and pending claims clearly flagged (e.g. "blocking 1 asset"), so that compliance risk is visible.
35. As an operator, I want a Home flagged-claim CTA to deep-link to the exact Brand section, so that resolving a flag is direct.

### Performance

36. As an operator, I want headline metrics (Reach, Engaged CTR, New subscriptions, CAC) with deltas vs. prior, so that I see results at a glance.
37. As an operator, I want a "why this is happening" section explaining the drivers, so that numbers come with narrative.
38. As an operator, I want a "what to change" section of concrete recommendations, so that I know the next move.
39. As an operator, I want a "what's working — keep" section, so that I don't break what's succeeding.

### Onboarding wizard (new, in mockup's design language)

40. As a new customer, I want a multi-step onboarding wizard collecting the core company/customer/positioning/brand/compliance information, so that the system has the durable context it needs.
41. As a new customer, I want to move forward/back between steps with a visible progress indicator, so that I can complete onboarding at my pace.
42. As a new customer, I want required-field validation before advancing, so that I don't submit incomplete context.
43. As a new customer, I want completing onboarding to populate the Brand screen with what I entered, so that my inputs become durable, reviewable brand context.
44. As a new customer, I want the wizard to reflect that AI extraction is not yet available (manual entry), so that my expectations match Milestone 1.

### New-campaign wizard (new, in mockup's design language)

45. As an operator, I want a new-campaign wizard collecting the campaign request, objective, audience, offer, budget, timeline, and channels (the minimum required inputs), so that a campaign starts with what strategy needs.
46. As an operator, I want to select from existing audience segments rather than retype them, so that campaigns inherit onboarding context.
47. As an operator, I want a review step summarizing my inputs before creating, so that I can confirm before committing.
48. As an operator, I want creating a campaign to add a row to the Campaigns table and open its Workspace at the Brief stage showing my entered brief, so that I can immediately continue the flow.
49. As an operator, I want required-input validation matching the "minimum required campaign inputs," so that a campaign can't start half-defined.

### Cross-cutting

50. As an operator, I want a single consistent status taxonomy (Draft, Needs input, In progress, Ready for review, Approved, Scheduled, Published, Needs attention, Not started) with consistent colors, so that state reads the same everywhere.
51. As an operator, I want my demo interactions (approvals, created campaigns, onboarding entries) to survive a page refresh within a session, so that a walkthrough isn't reset by accident.
52. As a developer, I want the app to pass typecheck, lint, and a browser smoke suite, so that the clone stays green as it grows.

## Implementation Decisions

- **App location & tooling.** One Next.js app at `web/` (App Router, TypeScript strict), sibling to `agent-harness/`. Node package manager: **pnpm**. ESLint + Prettier. Per [ADR-0012](../../docs/adr/0012-nextjs-frontend-and-bff-in-monolith.md).
- **No backend calls in M1.** Every screen renders from mock fixtures. The FastAPI engine is untouched; BFF→FastAPI wiring is a later milestone.
- **Styling.** Tailwind + **shadcn/ui**, re-themed to the mockup's design tokens (indigo `#4F46E5`, slate scale, status colors, radii), Instrument Sans via `next/font/google`. Icons via `lucide-react` (the mockup's nav glyphs are lucide paths).
- **Routing.** Real App Router routes: `/` (Home), `/campaigns`, `/campaigns/[slug]` (Workspace), `/calendar`, `/brand`, `/performance`, plus `/onboarding` and `/campaigns/new` (wizards). A shared layout renders the nav rail + shell.
- **State — single client store (Zustand).** Holds the mutable demo state seeded from fixtures: `approved`, selected `stage`, `calMode`, `calSelIdx`, `brandIdx`, `aiKey`, `rightTab`, plus the fixture collections (campaigns, calendar items, brand sections) and any campaigns/brand data created via the wizards. Persisted to `sessionStorage`. This is the seam that reproduces cross-screen reactivity (approving Strategy updates Home stats/queue and campaign status). Store shape, from the prototype:

  ```
  state = { view, stage: 2, approved: false, calMode: 'calendar',
            calSelIdx: 0, brandIdx: 0, aiKey: null, rightTab: 'evidence' }
  // status taxonomy → [bg, fg] color pair, shared by every status pill:
  ST = { Draft, 'Needs input', 'In progress', 'Ready for review',
         Approved, Scheduled, Published, 'Needs attention', 'Not started' }
  ```

- **Mock fixtures.** A `lib/mock-data` module holding the exact Fernway data from the prototype: campaigns, the 8-stage `stageDetails`, calendar `items` (channel/campaign/audience/funnel/pillar/status/perf), the 9 brand sections, evidence sources, performance blocks, and the Home queue. New content is layered on top of these in the store.
- **Status taxonomy is canonical.** The nine statuses and their colors live in one place and every status pill reads from it (no per-screen color literals).
- **Wizards produce store state, not API calls.** Onboarding writes into the Brand data structure; new-campaign appends a campaign and opens its Workspace. Both cover the **core / minimum-required** fields from the `development/` docs — not every exhaustive field — and include no AI extraction.
- **New-campaign Workspace fidelity.** A created campaign opens at the **Brief** stage rendered from its entered data; the deeper stages (populated evidence panel, AI notes, brand scorecard) keep the Fernway demo content, since only that campaign is designed. Noted limitation, not a defect.
- **Product name.** "Marketing OS" everywhere; "Cadence" in the mockup is a placeholder.
- **Responsive.** Desktop matches the mockup exactly; mobile/tablet behavior (drawer nav, stacking columns, tables→cards) is invented sensibly and refined later.
- **Open item (deferred).** The mockup's 8 operator stage names do not map 1:1 to the engine's 6 pipeline stages; the mapping is resolved at wiring time (recorded in ADR-0012). M1 uses the mockup names against mock data.

## Testing Decisions

- **Highest seam = the browser.** Tests drive the running Next.js app with **Playwright** and assert user-visible behavior through the UI — not store internals or component props. This is the single test seam; the Zustand store is exercised _through_ it. This matches the agreed quality gate and mirrors the backend's preference for testing at the outermost honest boundary (the API/CLI, per the harness tests).
- **A good test asserts external behavior:** a route renders its key content, navigation changes the URL and the active nav, and a flow produces a visible cross-screen effect. It does **not** assert Tailwind classes, DOM structure, or store field names.
- **Smoke suite (M1 scope):**
  - Each of the 6 screens + 2 wizard entry routes renders its headline content.
  - Nav moves between views and reflects the active item.
  - **Approve flow:** approving Strategy in a Workspace updates that campaign's status and the Home pending-approvals count.
  - **Onboarding flow:** completing the wizard shows the entered data on the Brand screen.
  - **New-campaign flow:** completing the wizard adds the campaign to the Campaigns table and opens its Workspace at Brief.
  - Calendar mode toggle switches grid/list/by-campaign; selecting an item shows its detail.
- **Static gates:** `tsc --noEmit` (strict) and ESLint/Prettier must pass. No exhaustive RTL unit tests for presentational components in M1.
- **Prior art:** none in the JS layer yet (this is the first FE); the backend's black-box API tests under `agent-harness/tests/` are the philosophical model — assert behavior at the boundary, not internals.

## Out of Scope

- Any call to the FastAPI engine or LangGraph pipeline; all data is mock. (Later milestone.)
- The BFF route handlers actually talking to the backend; the FE↔engine stage-name mapping. (Later milestone.)
- AI extraction from uploaded documents during onboarding (explicitly V2 per `development/onboarding-flow.md`).
- Authentication, multi-tenant/customer switching, real persistence beyond `sessionStorage`.
- Exhaustive coverage of every field in the `development/` flow docs (M1 = core/minimum-required only).
- Per-campaign deep Workspace content beyond the Fernway demo (created campaigns show Brief only, then Fernway content).
- A polished, fully-specified mobile design (responsive behavior is invented, to be refined).
- Component unit tests / visual-regression tests.

## Further Notes

- The mockup is a self-contained prototype; its component source (a `DCLogic` class with a `renderVals()` method) is the ground truth for exact data, status colors, stage copy, and interaction logic. Extract data and copy from it verbatim rather than paraphrasing.
- "Approve" in the prototype is a single global boolean that fans out to Home, Campaigns, and Workspace — the store must reproduce that fan-out, not just local Workspace state.
- Slice order suggestion for `/to-issues`: (1) scaffold `web/` + tooling + shell/nav + design tokens, (2) status taxonomy + shared primitives, (3) Home, (4) Campaigns + Workspace + approve flow, (5) Calendar, (6) Brand, (7) Performance, (8) onboarding wizard → Brand, (9) new-campaign wizard → Campaigns/Workspace, (10) Playwright smoke suite. Each is a vertical, visible slice.

## Completion

- Completed: 2026-07-16
- Commit: `5151e8f0dcaf505eead1ccdc67e022c8f475316d`

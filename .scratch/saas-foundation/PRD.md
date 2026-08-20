# PRD: we-OS SaaS foundation — tenancy, persistence, approval gates, and FE↔engine wiring

Status: ready-for-agent
Category: feature
Date: 2026-08-20

Governed by ADRs [0013](../../docs/adr/0013-multi-tenant-saas-with-dual-verified-jwt.md), [0014](../../docs/adr/0014-postgres-system-of-record-and-split-governance.md), [0015](../../docs/adr/0015-human-approval-gates-and-versioned-deliverables.md), [0016](../../docs/adr/0016-channel-planning-precedes-creative.md), [0017](../../docs/adr/0017-stages-and-lifecycle-are-separate-axes.md), [0018](../../docs/adr/0018-human-authored-dna-from-a-curated-questionnaire.md), [0020](../../docs/adr/0020-usage-ledger-and-enforced-quota.md), [0022](../../docs/adr/0022-brand-dna-and-the-overloaded-customer.md). Vocabulary per [CONTEXT.md](../../CONTEXT.md).

## Problem Statement

A business owner cannot use we-OS. The engine that does the actual work — the mandatory pipeline, the DNA Gate, the QA loop against Guardrails, cancellable runs, run traces — is built and green. The designed frontend exists as a faithful mockup. **Nothing connects them, and nothing underneath them supports more than one business.**

Concretely, today:

- There is **no identity**. No user, no tenant, no login. Every endpoint takes the business identity as a caller-supplied parameter and verifies nothing, so any caller who can reach the port can read any business's strategy, research, and campaign plans.
- There is **no way to get a Brand DNA into the system**. It is human-authored markdown that agents may never write, and no endpoint creates or updates it. The onboarding wizard collects answers that have nowhere to go — and under-collects: four Required DNA fields (price point, geography/service area, languages, budget range) and two of the three Required KPI tiers are never asked for, so **every business completing onboarding today would fail the DNA Gate**.
- Both wizards ask the business owner to supply work the engine owes them — value proposition, customer promise, differentiators, channel selection — which is the hardest strategic work, demanded at signup, on a blank page.
- There is **no way to read a deliverable**. The API reports filenames and byte sizes. The Workspace screen has nothing to render.
- There is **no human approval**. A run executes all stages back-to-back gated only by the model reviewer, so creative is produced from strategy no person ever approved — contradicting the documented constraint that creative is never generated before an approved strategy exists.
- **Runs do not survive a restart**, and the per-slug concurrency guard is process-local, so the service cannot run more than one worker.
- The frontend's eight step names do not map onto the engine's six stages, and that mapping was explicitly deferred to wiring time.

The result: a business owner has no way to sign up, describe their business, run a campaign, see what came back, or say yes to it.

## Solution

A business owner signs up, is walked through a curated Questionnaire that asks only for facts they uniquely know, and lands on a complete Brand DNA. They create a campaign with a goal and success metrics, and start a Run. The engine researches, positions, and plans — **stopping at each Approval Gate** to show its work and wait for a decision. The owner reads the deliverable, and either approves it or sends it back with feedback, which produces a new version rather than overwriting the old one. Approved upstream, the run continues. If they later re-open an approved decision, everything downstream is marked Stale rather than silently regenerated.

Underneath, every byte is owned by a Tenant derived from a verified identity claim, held in Postgres behind a `DocumentStore` port, with every billable model call metered against that tenant's allowance.

From the business owner's perspective: **they answer honest questions about their business, and a marketing department goes to work — checking in with them at each decision that matters.**

## User Stories

### Identity and tenancy

1. As a business owner, I want to sign up and log in, so that my marketing work is mine and persists between sessions.
2. As a business owner, I want everything I create to belong to my business alone, so that no other we-OS customer can see my strategy, research, or campaign plans.
3. As a business owner, I want to stay logged in across page reloads, so that I am not re-authenticating constantly.
4. As a business owner, I want to log out, so that I can leave a shared machine safely.
5. As a business owner, I want a request without a valid identity to be refused, so that my data is not reachable by an unauthenticated caller.
6. As a business owner, I want a request carrying a valid identity for a *different* business to be refused access to my data, so that a bug or a crafted request cannot cross the tenant boundary.
7. As the platform admin, I want tenant scoping enforced in the storage layer rather than at each endpoint, so that a forgotten filter in new code cannot leak data.
8. As the platform admin, I want the engine to verify identity independently of the frontend, so that reaching the engine directly does not bypass tenancy.

### Onboarding and the Brand DNA

9. As a business owner, I want to be guided through a set of questions about my business, so that I can describe it accurately without knowing marketing theory.
10. As a business owner, I want each question to explain **why** it is being asked and what a good answer looks like, so that I answer usefully rather than guessing.
11. As a business owner, I want to be asked only for facts I actually know — what I sell, at what price, to whom, why they choose me, where, in what languages, under what constraints — so that onboarding is answerable rather than a strategy exercise.
12. As a business owner, I want we-OS to produce my positioning, value proposition, messaging, and brand voice rather than asking me for them, so that I get the expertise I am paying for.
13. As a business owner, I want to describe my audience segments and rank them, so that campaigns can target a specific group rather than everyone.
14. As a business owner, I want to save partway through onboarding and come back, so that I can gather information I do not have to hand.
15. As a business owner, I want to see how much of my Brand DNA is complete and what is still missing, so that I know what stands between me and starting work.
16. As a business owner, I want to edit any Brand DNA answer later, so that I can correct it as my business changes.
17. As a business owner, I want my Brand DNA to be mine to author, never generated from scraping my website, so that what the system believes about my business is actually true.
18. As a business owner, I want to be told exactly which Required fields are incomplete when I try to start work, so that I can fix them rather than guess.
19. As a business owner whose Brand DNA predates a new question, I want to be prompted to answer the new questions, so that I am not silently blocked by a gate that changed under me.
20. As the platform admin, I want to curate the question set myself, so that the questions reflect professional marketing practice rather than a model's guess at what to ask.
21. As the platform admin, I want to edit and publish a new version of the question set without a deploy, so that I can improve onboarding as I learn from real businesses.
22. As the platform admin, I want changing the question set to automatically change what the DNA Gate requires, so that the questionnaire and the gate cannot drift apart.

### Campaigns and goals

23. As a business owner, I want to create a campaign with a name, so that I can run distinct pushes for distinct objectives.
24. As a business owner, I want to state one measurable business objective for the campaign, so that every downstream recommendation ties back to it.
25. As a business owner, I want to set a timeframe and a campaign budget, so that the plan is bounded by what I can actually spend.
26. As a business owner, I want to pick which of my audience segments the campaign targets, so that the work is specific rather than generic.
27. As a business owner, I want to be asked for all three KPI tiers — business, marketing, and creative — so that the campaign has a complete definition of success.
28. As a business owner, I want we-OS to choose my channels rather than asking me to, so that channel selection is an expert decision rather than my guess.
29. As a business owner, I want to see all my campaigns with their status and where each one has got to, so that I can track everything in flight.
30. As a business owner, I want to be told what is blocking a campaign, so that I can unblock it.
31. As a business owner, I want to archive a campaign I am no longer running, so that my list reflects reality.

### Running the pipeline

32. As a business owner, I want to start a run from the campaign, so that work begins.
33. As a business owner, I want the run to be refused with a clear list of what is missing if my Brand DNA or campaign goal is incomplete, so that I fix inputs rather than get generic output.
34. As a business owner, I want to watch progress live as each stage works, so that I can see the system is doing something.
35. As a business owner, I want to close the tab and come back to a run still in progress, so that I am not tethered to the browser.
36. As a business owner, I want a run to survive a service restart, so that a deploy does not destroy work in progress.
37. As a business owner, I want to cancel a run, so that I can stop work I no longer want.
38. As a business owner, I want a cancelled run to start clean next time rather than resuming, so that cancelling means what it says.
39. As a business owner, I want to be prevented from starting a second run of the same campaign while one is active, so that two runs cannot fight over the same campaign.
40. As a business owner, I want to see a run's history after it finishes, so that I can review what happened.
41. As a business owner, I want a failed run to tell me what went wrong in language I can act on, so that I am not stuck.

### Approval gates and revision

42. As a business owner, I want the run to stop and ask me before it acts on a major decision, so that the strategy is mine and not the machine's.
43. As a business owner, I want to see which stages need me and which the system handles itself, so that I know when to expect an interruption.
44. As a business owner, I want to read the full deliverable at a gate, so that I can judge it properly rather than approving a summary.
45. As a business owner, I want to see the reasoning and evidence behind a recommendation, so that I can tell whether it is grounded in my business.
46. As a business owner, I want to approve a stage and have the run continue automatically, so that saying yes is one action.
47. As a business owner, I want to send a stage back with written feedback, so that I can get what I actually need rather than accepting what I was given.
48. As a business owner, I want my feedback to produce a new version rather than overwrite the old one, so that I can see what changed and why.
49. As a business owner, I want to compare a deliverable's versions, so that I can tell whether my feedback was understood.
50. As a business owner, I want to see the feedback that prompted each version, so that the history explains itself months later.
51. As a business owner, I want creative work to be impossible before I have approved the strategy it rests on, so that the system cannot produce assets off decisions I never made.
52. As a business owner, I want to re-open a stage I approved earlier, so that I can change my mind as I learn.
53. As a business owner, I want re-opening a stage to mark everything downstream as stale rather than regenerating it, so that nothing is rewritten (and no budget spent) without my say-so.
54. As a business owner, I want stale work clearly marked in the interface, so that I never act on a plan built on a superseded decision.
55. As a business owner, I want to re-run the stale stages when I am ready, so that I control when the work is redone.
56. As the platform admin, I want which stages require human approval to be configuration rather than code, so that I can tune the friction without a rewrite.

### Deliverables and the workspace

57. As a business owner, I want to read every deliverable the system has produced for a campaign, so that I own the thinking and not just the output.
58. As a business owner, I want the stage stepper to show me where the campaign is, what is done, and what is next, so that I understand the journey.
59. As a business owner, I want the interface to speak plain marketing language rather than internal stage keys, so that it is usable by someone who is not an engineer.
60. As a business owner, I want to see the campaign's overall status separately from its stage progress, so that "waiting on me" and "at stage 4" are not confused.
61. As a business owner, I want to see the channel plan and placements before the creative brief, so that the creative is scoped to where it will actually run.
62. As a business owner, I want to see which framework or evidence a recommendation draws on, so that I can trust it.
63. As a business owner, I want to know when a recommendation could not be made because my Brand DNA lacks something, so that I can supply the missing fact instead of receiving invented filler.

### Cost and quota

64. As a business owner, I want to see how much of my allowance I have used, so that I am not surprised.
65. As a business owner, I want to be told clearly when I have run out of allowance, so that I understand why work stopped.
66. As a business owner, I want a limit on how many times a single piece of work can be revised, so that I cannot accidentally burn my whole allowance on one item.
67. As the platform admin, I want every billable model call recorded against its tenant with its cost, so that I know what a campaign, a revision, and a business actually cost me.
68. As the platform admin, I want the allowance checked *before* a billable call rather than after, so that a runaway loop cannot overspend.
69. As the platform admin, I want quota exhaustion to be a first-class, typed failure on every endpoint that can trigger work, so that the frontend can handle it properly rather than showing a generic error.

### Platform administration

70. As the platform admin, I want to edit the Guardrail rubrics without a deploy, so that I can raise the quality bar as I learn what the reviewer lets through.
71. As the platform admin, I want to add frameworks to the Knowledge Library without a deploy, so that the specialists' expertise deepens over time.
72. As the platform admin, I want the eight non-negotiable rules, the pipeline definition, and the specialist prompts to stay in code and go through review, so that agent behaviour cannot be changed by an unreviewed edit.
73. As the platform admin, I want to see runs across all tenants, so that I can spot failures before customers report them.

### Frontend wiring

74. As a business owner, I want the frontend to show my real data rather than fixtures, so that the product is real.
75. As a business owner, I want an action I take on one screen to be reflected on the others, so that the app is coherent.
76. As a business owner, I want a clear loading state while the engine works, so that I know the system is not stuck.
77. As a business owner, I want a failed request to tell me what happened and what to do, so that I am not left staring at a blank screen.
78. As a business owner, I want the app to work on my phone, so that I can approve something without opening a laptop.

## Implementation Decisions

### Tenancy and identity

- A **Tenant is one business**. we-OS is not an agency platform: one tenant owns exactly one Brand DNA and many campaigns. The people a business sells to are Audience Segments *inside* the Brand DNA, not managed entities ([ADR-0013](../../docs/adr/0013-multi-tenant-saas-with-dual-verified-jwt.md), [ADR-0022](../../docs/adr/0022-brand-dna-and-the-overloaded-customer.md)).
- Identity comes from a managed IdP issuing JWTs. The BFF verifies the token for rendering **and** forwards it; the engine verifies it independently and derives the tenant from the verified claim. **No endpoint accepts a business identity as a caller-supplied parameter** — the existing `customer` parameter is removed, not validated, because under one-business-per-tenant it is fully redundant.
- Tenant scoping is enforced in the repository/`DocumentStore` layer and backstopped by Postgres row-level security, never at individual call sites.
- The specific IdP is deliberately left open; it sits behind the auth dependency and is reversible.

### Storage

- Postgres becomes the system of record for tenant data, LangGraph checkpoints, the Questionnaire, the Guardrails and the Knowledge Library. The eight rules, the pipeline definition and the specialist prompts stay code-shipped ([ADR-0014](../../docs/adr/0014-postgres-system-of-record-and-split-governance.md)).
- A new **`DocumentStore` port** resolves documents per tenant. **Markdown stays the agent I/O format** — only *where a document lives* moves, so the DNA Gate's template parsing, the rubrics, and every specialist prompt are unchanged. Adapters: in-memory (tests), filesystem (local development), Postgres (production).
- Deliverables are **immutable and versioned**. A revision writes a new version carrying the feedback that prompted it and a pointer to what it supersedes; nothing is overwritten.
- Once the checkpointer is durable, **abandoning a cancelled run must explicitly clear its checkpoint threads** (both the full-pipeline thread and any per-stage thread), or "a cancelled run starts clean" silently becomes "resume from the last checkpoint".
- A durable, shared run registry replaces the in-process one, which is the prerequisite for running more than one worker.

### The Questionnaire and the DNA Gate

- The admin-curated question set is versioned in Postgres and is the single artifact driving the wizard UI, the shape of the rendered Brand DNA, and what the DNA Gate enforces as Required ([ADR-0018](../../docs/adr/0018-human-authored-dna-from-a-curated-questionnaire.md)).
- Each question carries: a stable id, the question text, why it is asked, help text, input type, required/recommended, and the DNA field it populates.
- Answers are stored structured and **rendered into canonical Brand DNA markdown**, which is what agents read. The structured record is the source of truth; the markdown is a derived projection.
- The gate's existing behaviour is preserved: Required fields are derived from the question set, so adding a question tightens the gate with no code change.
- Publishing a new question-set version does not retroactively fail existing tenants; it surfaces the unanswered questions as an explicit prompt.
- The wizard is rewritten to collect the four missing Required DNA fields and all three KPI tiers, and to **remove** the crafted-artifact questions (value proposition, customer promise, differentiators, channel selection).

### Pipeline and approval

- **The pipeline is reordered** so the Performance Plan is stage 4, before the Creative Brief, and the creative stages inherit the channel mix and Placements ([ADR-0016](../../docs/adr/0016-channel-planning-precedes-creative.md)):
  `research → brand-strategy → campaign-strategy → performance-plan → creative-brief → asset-prompts`
- Each Stage carries an **approval policy** — `auto` or `human`. Defaults: research `auto`; brand-strategy, campaign-strategy, performance-plan, creative-brief and asset-prompts `human`. The policy is data, so tuning it is a configuration change.
- A `human` stage halts via a LangGraph `interrupt()` and resumes on an explicit approve or revise call. The run API gains approve and revise operations alongside the existing start, status, cancel and stream ([ADR-0015](../../docs/adr/0015-human-approval-gates-and-versioned-deliverables.md)).
- Re-opening an approved stage marks downstream deliverables **Stale**; stale work is never auto-regenerated.

### API contract and vocabulary

- **The OpenAPI contract is frozen before implementation begins** and is the artifact the frontend codes against, so FE and BE proceed in parallel against a mock server.
- The API speaks **engine stages only**. A separate campaign lifecycle status carries `draft`/`running`/`awaiting_approval`/`approved`/`published`/`measuring`/`archived`, and each stage reports the operator **Phase** it belongs to, so the frontend renders its designed stepper without the engine adopting UI vocabulary ([ADR-0017](../../docs/adr/0017-stages-and-lifecycle-are-separate-axes.md)).
- A deliverable-read operation is added — the current API exposes filenames and sizes only, and the Workspace cannot render without content.
- Errors keep the existing pattern of carrying their own HTTP status and structured detail, extended with a typed quota failure surfaced as 402 ([ADR-0020](../../docs/adr/0020-usage-ledger-and-enforced-quota.md)).

### Cost

- A usage ledger records every billable call — tokens and, later, image generations — against its tenant with its cost. The allowance is checked **before** each billable call and recorded after. Hard caps bound revisions per deliverable and runs per campaign.
- How the allowance is *presented* (credits, fair use, metered billing) is deliberately deferred; the mechanism is not.

## Testing Decisions

**What makes a good test here:** it asserts what a business owner or an API client can observe — status codes, payloads, which stage the run reached, what the gate reported, whether a second tenant could see anything — and never reaches into graph internals, private helpers, or storage layout. A test that would break under a refactor that preserved behaviour is a bad test. The suite must stay hermetic and offline: no network, no real model calls, no live IdP.

**Seams (agreed with the developer):**

- **The HTTP API via `TestClient` is the default seam for everything.** Strong prior art already exists: the current API tests drive every endpoint with a scripted chat model and a fake reviewer against a hermetic repository fixture, clearing the settings and registry caches per test. All new behaviour — auth rejection, cross-tenant refusal, questionnaire → DNA → gate, run → `awaiting_approval` → approve/revise, version history, staleness, quota 402 — is asserted here.
- **The gate as a pure function** stays a seam, for deriving Required fields from a question-set version and reporting precisely which are missing. Prior art: the existing gate tests.
- **The graph runner with a scripted model** stays a seam, for stage order, prerequisite enforcement, and interrupt/resume mechanics that would need many HTTP round trips to observe. Prior art: the existing graph and cancellation tests.
- **The `DocumentStore` port** is the one significant new seam. An in-memory adapter backs every fast test, so nothing touches a database or the filesystem.
- **The auth dependency** is a new, minimal seam, overridable per test to inject a verified tenant claim — following the existing cache-clearing idiom for settings and the run registry.

**Adapter conformance:** one contract suite runs the *same* assertions against both the in-memory and the real Postgres `DocumentStore` (containerised), covering tenant isolation, row-level security, version ordering, and staleness propagation. This is deliberate: an in-memory fake cannot honestly model transactions, constraints or RLS, and tenant isolation is the highest-severity bug class in this PRD. That suite is marked slow and skippable locally; Docker becomes a test dependency in CI.

**Specifically to be covered:**

- A run cancelled mid-stage and then restarted begins from stage 1 rather than resuming from its checkpoint.
- A request with no identity, and a request whose identity belongs to another tenant, are both refused for every resource type.
- A campaign whose Brand DNA is missing Required fields is refused a run, and the response names each missing field.
- A `human`-policy stage halts, and the run does not advance until an explicit approval.
- A revise produces a new version, preserves the prior one, and records the feedback.
- Re-opening an approved stage marks downstream deliverables stale without regenerating them.
- Exhausted quota refuses a run and a revise with the typed error.
- The frontend suite keeps its existing thin smoke-test gate; presentational UI is not exhaustively unit-tested.

## Out of Scope

- **Creative unit generation** — copy + still image + Placement, the `ImageGenerator` port, binary storage, and the asset review loop ([ADR-0019](../../docs/adr/0019-creative-unit-is-the-approvable-asset.md)). Its own PRD, once this foundation lands. This PRD carries the versioning and approval machinery it will reuse.
- **Meta and TikTok integration** — Platform Connections, OAuth, encrypted token storage, the `PublishTarget` port, organic publishing, and paid ads ([ADR-0021](../../docs/adr/0021-organic-publishing-before-paid-ads.md)). Its own PRD.
- **Billing and payments.** The usage ledger and quota enforcement are in scope; charging money is not.
- **Self-serve signup at scale**, pricing pages, and plan management. Design-partner onboarding is enough.
- **The post-launch Measure and Optimize loop.** The lifecycle statuses exist; the operational loop behind them does not.
- **Knowledge Library content and Guardrail sharpening.** This PRD moves them to an editable store; filling them with domain expertise is tracked separately as `.scratch/backfill/issues/03` and `06`.
- **Removing `customer` from the harness internals.** Tracked as `.scratch/tenant-vocabulary/issues/01`, sequenced with the Postgres migration.
- **Retiring the `.claude/` layer.** It remains a development and authoring surface.

## Further Notes

- **Sequencing is load-bearing.** The FE cannot be wired first: auth, tenancy, Postgres, versioned deliverables and the approve/revise operations all change the contract it would bind to. Postgres is a **hard prerequisite** for approval gates, because LangGraph cannot resume an interrupted run across a process boundary on an in-memory checkpointer. The order is: freeze the contract → foundation → one vertical tracer bullet end-to-end → full wiring.
- **Start the Meta Business Verification and TikTok audit applications now**, in parallel with this work. They are calendar time, not engineering time, and they gate a later PRD entirely.
- The engine itself is in good shape and this PRD does not relitigate it: the pipeline, gate, QA loop, cancellation, tracing and web-search fallback chain are green (189 passed, 1 skipped; ruff and mypy clean) and are being *rehomed*, not rebuilt.
- The correction that a Tenant is one business — not an agency managing many — **simplifies** this work: no customer-selection UI, no per-customer routing, and the Brand DNA is a singleton on the tenant rather than a collection.

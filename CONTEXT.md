# we-OS (Marketing OS)

A SaaS agentic platform that gives a business a cheaper alternative to hiring a marketing team or retaining an agency. It is a **decision-making system**, not a content generator: it replicates the strategic process a professional marketer follows *before* assets are created, and content is a downstream tool, never the goal. Each tenant is one business marketing itself (see [ADR-0013](docs/adr/0013-multi-tenant-saas-with-dual-verified-jwt.md)). The engine exists as the `agent-harness/` LangGraph application, with `.claude/` as its interactive development and authoring surface. See [docs/adr/](docs/adr/) for the decisions behind the current shape.

## Language

**Tenant**:
One business using we-OS to market itself — the isolation boundary for all data in the system. A tenant owns exactly one Brand DNA, and many campaigns. we-OS is not an agency platform: a tenant never manages other businesses (see [ADR-0013](docs/adr/0013-multi-tenant-saas-with-dual-verified-jwt.md)).
_Avoid_: account, org, workspace, client, agency.

**Tenant-Owned Document**:
Anything that belongs to one business and no other — its Brand DNA, campaign goals, deliverables, and run traces. Reachable only by naming the tenant that owns it, because the tenant is part of where the document lives rather than a filter applied afterwards. A tenant-owned document is never served to an agent by the read sandbox; it resolves through the tenant-scoped `DocumentStore` (see [ADR-0023](docs/adr/0023-tenant-partitioned-storage-and-a-sandbox-that-serves-no-tenant-data.md)).
_Avoid_: user data, private file, scoped document.

**Code-Shipped Material**:
The governance the platform ships and every tenant shares — the eight rules, the pipeline definition, specialist prompts, templates, guardrails, the Knowledge Library. Identical for every business, which is what makes it safe to read unscoped. The counterpart to a Tenant-Owned Document, and the only thing the read sandbox serves.
_Avoid_: static files, config, assets.

**Brand DNA**:
The stable, reusable, human-authored profile of the tenant's business — what it sells, at what price, where, under what constraints, in what voice, and to which audience segments. The single source of truth every recommendation is grounded in. One per tenant, reused across every campaign; read-only to agents. Authored by answering the Questionnaire — never drafted or guessed by a model (see [ADR-0018](docs/adr/0018-human-authored-dna-from-a-curated-questionnaire.md)).
_Avoid_: "Customer DNA" (the old name — it implied an agency serving many businesses), profile, brief, persona.

**Customer**:
A person or organization the tenant's business sells to. Customers are described in the Brand DNA as audience segments; they are never users of we-OS and never entities the tenant administers.
_Avoid_: using "customer" for the tenant, the business, or the platform's own user.

**Audience Segment**:
One named group of the tenant's customers, defined inside the Brand DNA and ranked by strategic priority. A campaign targets exactly one segment — which is what makes a campaign specific rather than generic.
_Avoid_: persona, audience, target market, cohort.

**Questionnaire**:
The admin-curated set of questions a business answers to author its Brand DNA. It asks only for **facts the business owner uniquely knows** — never for crafted artifacts like positioning or channel choice, which the pipeline produces. One artifact drives three things: the onboarding wizard, the shape of the DNA, and what the DNA Gate enforces as Required.
_Avoid_: survey, form, intake, onboarding flow.

**Campaign Goal**:
The per-campaign business objective and success metrics (`campaigns/<slug>/goal.md`). The DNA is shared across campaigns; the goal is specific to one. It never names the business — a tenant is one business, so which business the campaign belongs to is already known.
_Avoid_: objective doc, spec.

**Campaign Slug**:
The identifier for a single **campaign** — the durable thing. It names the campaign's directory (`campaigns/<slug>/`, resolved within the owning tenant), so every input and deliverable for that campaign lives under it, and it keys the checkpoint thread that makes the campaign resumable. A slug is unique within a tenant, not globally: two businesses may both run a campaign called `spring` without ever meeting. A specialist must use the campaign's slug verbatim; a write under any other slug is rejected as off-slug (see [ADR-0006](docs/adr/0006-recoverable-tool-errors-and-slug-anchored-seeds.md)).
_Avoid_: id, name, key, thread.

**Run**:
A single **execution attempt** of a campaign's pipeline, identified by a unique `run_id`. A campaign (slug) may accumulate many runs over its life — one per attempt — but **at most one run per slug may be active at a time** (a second concurrent run of the same slug is rejected). Each run has its own JSONL trace (`logs/<tenant>/<slug>/<run_id>.jsonl` — a run is a Tenant-Owned Document, so a run id is unfindable outside the tenant that owns it) and, in the background-job model, its own status and cancellation handle. The slug names the campaign; the run_id names one attempt to advance it. A run's **status** is one of: **running** (executing now), **completed** (finished ok), **failed** (halted on an error), **cancelled** (stopped on operator request), or **interrupted** (its process died — e.g. a restart — leaving a trace with no terminal summary). Cancelling a run **abandons** it: it is not resumed, and the next run of the slug starts clean. See [ADR-0010](docs/adr/0010-background-job-run-model.md) for the background-job model and [ADR-0009](docs/adr/0009-async-cancellable-pipeline-execution.md) for the cancellable async foundation it rests on.
_Avoid_: job (use for the background execution mechanism only), execution, session, thread.

**Marketing Director**:
The orchestrator (the `/new-campaign` skill / main session). Runs the DNA gate, sets the business goal and campaign strategy, and delegates to specialists in mandatory order. Never produces research, strategy, creative, or assets itself.
_Avoid_: coordinator, manager, supervisor.

**Specialist**:
One of the five subagents, each running in isolated context with restricted tools and a single output type: **market-research** (findings), **brand-strategy** (positioning/messaging/value prop), **creative-director** (creative briefs), **creative-asset-prompt** (generation prompts), **performance-marketing** (channels/KPIs/budget/optimization).
_Avoid_: worker, sub-agent (spelled with hyphen inconsistently), expert.

**Deliverable**:
The markdown document a stage produces (e.g. `research.md`, `brand-strategy.md`). A stage's deliverable existing is the prerequisite for the next stage. Deliverables are **immutable and versioned**: a revision writes a new version carrying the feedback that prompted it, and never overwrites (see [ADR-0015](docs/adr/0015-human-approval-gates-and-versioned-deliverables.md)).
_Avoid_: output, artifact, document.

**Stale**:
The state of a deliverable whose upstream decision has since been re-opened and re-approved. A stale deliverable is not silently regenerated — it requires an explicit re-run, so creative never rests on superseded strategy without someone noticing.
_Avoid_: outdated, dirty, invalidated.

**Stage**:
One step of the mandatory pipeline, owned by exactly one role, producing exactly one deliverable. Stages never run out of order and never skip an upstream decision. Each stage carries an **approval policy** — `auto` (advance when the reviewer passes it) or `human` (halt at an Approval Gate).
_Avoid_: step, task.

**Phase**:
The operator-facing grouping of stages the UI presents (`Brief · Research · Strategy · Plan · Produce`). A phase may cover more than one stage — `Strategy` covers brand-strategy and campaign-strategy. Phases are presentation; stages are canonical (see [ADR-0017](docs/adr/0017-stages-and-lifecycle-are-separate-axes.md)).
_Avoid_: step, stage (a phase is not a stage).

**Approval Gate**:
The point where a `human`-policy stage halts and waits for a person to approve the deliverable or send it back with feedback. Distinct from the QA reviewer, which is a model scoring against a Guardrail; the gate is a human decision, and it is what makes this a decision-making system rather than a generator.
_Avoid_: sign-off, checkpoint (reserved for LangGraph state), review (reserved for QA).

**Campaign Lifecycle Status**:
Where a campaign sits as a whole — `draft`, `running`, `awaiting_approval`, `approved`, `published`, `measuring`, `archived`. A separate axis from stage progress: `Approve`, `Publish` and `Measure` are lifecycle, not pipeline stages.
_Avoid_: state, stage, phase.

**DNA Gate**:
The mandatory Stage 0 check: complete Brand DNA + complete Campaign Goal must both exist before any campaign work begins. On failure it lists what is missing and stops.
_Avoid_: precondition, validation.

**Guardrail** (a.k.a. **Rubric**):
A human-written QA standard a deliverable is scored against before the next stage may begin. A shared rubric applies to every deliverable; one per stage adds stage-specific checks. Admin-tunable content, so it lives in the database rather than in code (see [ADR-0014](docs/adr/0014-postgres-system-of-record-and-split-governance.md)).
_Avoid_: check, test, lint.

**Knowledge Library**:
The central, citable store of expert frameworks by discipline. Read-only to agents; agents cite which framework they applied. Admin-tunable, so it lives in the database. Currently stubs awaiting domain content.
_Avoid_: docs, references, wiki.

**Creative Unit**:
The approvable creative artifact: headline, primary text, CTA, one generated still image, and a named placement (e.g. Meta feed 1:1, TikTok 9:16). What gets published is an ad, not a picture, so the unit — not the image — is what a client approves or sends back (see [ADR-0019](docs/adr/0019-creative-unit-is-the-approvable-asset.md)).
_Avoid_: asset, creative, ad, post (each names only part of it).

**Placement**:
The platform-and-format slot a creative unit is built for, carrying its aspect ratio, dimensions and copy limits. Decided by the Performance Plan **before** the creative brief is written, so creative is never authored blind to its format.
_Avoid_: format, channel (a channel may have several placements), surface.

**Platform Connection**:
A tenant's authorized link to one external platform account (Instagram/Facebook Page, TikTok), holding the access tokens the system publishes and reads results through. Tokens are secrets at rest.
_Avoid_: integration, account, link.

**Campaign Budget**:
The client's **media/ad spend** for one campaign, allocated per channel by the Performance Plan. Distinct from generation cost, which is what the platform spends on models to produce the work.
_Avoid_: budget (unqualified), spend, cost.

**Usage Ledger**:
The per-tenant record of every billable model call — tokens and image generations — with its cost. Checked before a billable call and written after, so quota is enforced rather than merely observed (see [ADR-0020](docs/adr/0020-usage-ledger-and-enforced-quota.md)).
_Avoid_: metering, billing, telemetry.

**Web Backend**:
The pluggable live-web capability (`WebSearchTool` port) granting the specialists that declare it — market-research and performance-marketing — `web_search`/`web_fetch` tools. Adapters: the default **NoopWebSearch**, which returns an honest "web search is not configured" message so runs stay grounded in the Brand DNA; **TavilyWebSearch**, the primary backend calling Tavily's JSON API (`/search` + `/extract`) over plain HTTP with no browser (see [ADR-0011](docs/adr/0011-tavily-primary-web-backend.md)); **PlaywrightWebSearch**, a browser-driven backend scraping DuckDuckGo (see [ADR-0007](docs/adr/0007-thread-confined-sync-playwright-backend.md)); and **GoogleWebSearch**, which subclasses it to scrape `google.com/search`, reusing the same browser lifecycle and `fetch`. The live capability is off by default and wired only when `MARKETING_OS_WEB=1` (see [ADR-0001](docs/adr/0001-ports-and-adapters-architecture.md)).
_Avoid_: search tool, web tool, scraper.

**Backend Fallback Chain** (`FallbackWebSearch`):
An ordered composition of web backends that is itself a `WebSearchTool`, so the graph wiring is unchanged. `search` tries each backend in priority order and falls through to the next on a recoverable `ToolError` or an empty result set; the final backend's outcome (result or raised error) surfaces unchanged, so a single configured backend behaves exactly as one backend alone. The order is set by `MARKETING_OS_WEB_BACKENDS` — a comma-separated, priority-ordered list of `tavily` / `google` / `duckduckgo` / `noop` (default `tavily,google,duckduckgo`, i.e. Tavily's JSON API first, with the Google → DuckDuckGo scrapers as fallback; see [ADR-0011](docs/adr/0011-tavily-primary-web-backend.md)). When `tavily` is in the list but `MARKETING_OS_TAVILY_API_KEY` is unset it is **skipped with a warning** (omitted from the chain) and the run proceeds on the scrapers. Recoverable failures — Tavily quota/5xx/network/timeout, or Google's anti-automation responses (consent interstitial, `/sorry/` CAPTCHA, zero-parse markup) — are raised as recoverable `ToolError`s so the chain moves on rather than crashing the run; a rejected Tavily key instead raises a terminal `ConfigError` that stops the run. (See [ADR-0008](docs/adr/0008-google-scraping-web-search-with-fallback-chain.md) for why the fallback engines are scraped rather than called via an official API.)
_Avoid_: retry chain, backend pool, load balancer.

**KPI tiers**:
The three levels every campaign must define, which ladder up to each other — **Business KPI** (revenue, leads, bookings, retention), **Marketing KPI** (CTR, CPC, CPM, conversion rate), **Creative KPI** (hook rate, watch time, engagement rate).
_Avoid_: metrics, goals (unqualified).

## The mandatory pipeline

Each stage requires the prior stage's deliverable to exist; no stage bypasses an upstream decision (`.claude/rules/decision-hierarchy.md`, `agent-harness/src/marketing_os/governance/pipeline.py`).

| Stage | Phase | Owner | Deliverable | Approval |
| --- | --- | --- | --- | --- |
| 0 — DNA Gate | Brief | Marketing Director | *(gate; no file)* | — |
| 1 — Research | Research | market-research | `research.md` | auto |
| 2 — Brand Strategy | Strategy | brand-strategy | `brand-strategy.md` | human |
| 3 — Campaign Strategy | Strategy | Marketing Director | `campaign-strategy.md` | human |
| 4 — Performance Plan | Plan | performance-marketing | `performance-plan.md` | human |
| 5 — Creative Brief | Produce | creative-director | `creative-brief.md` | human |
| 6 — Asset Prompts | Produce | creative-asset-prompt | creative units | human |
| Launch → Analysis → Optimization | *(lifecycle)* | Marketing Director (+ performance-marketing) | *(operational loop)* | — |

The Performance Plan precedes creative so the brief and the asset prompts inherit the channel mix and placement specs (see [ADR-0016](docs/adr/0016-channel-planning-precedes-creative.md)).

## Hard constraints

- **DNA-grounded** — every recommendation traces to the Brand DNA or to research findings; generic filler is prohibited. If the DNA lacks what an agent needs, the agent says so rather than inventing.
- **Human-authored truth** — the Brand DNA is answered by the business, never drafted by a model. The business supplies facts; the system supplies craft (see [ADR-0018](docs/adr/0018-human-authored-dna-from-a-curated-questionnaire.md)).
- **Strategy before content** — creative is never generated before a **human-approved** strategy exists, which is what the Approval Gates enforce.
- **Upstream prerequisite** — a stage may not begin until the prior stage's deliverable exists.
- **QA budget** — each deliverable must pass its guardrail rubric within `MARKETING_OS_MAX_QA` revision rounds (default 3), or the run halts.
- **Tenant scope** — every read and write is scoped to the tenant derived from the verified identity claim, enforced in the storage layer rather than at call sites (see [ADR-0013](docs/adr/0013-multi-tenant-saas-with-dual-verified-jwt.md)). The tenant is part of where a document lives, so the unscoped call does not exist to be reached for; cross-tenant access answers **404, not 403**, so existence never leaks. Agents never see a tenant id and cannot read Tenant-Owned Documents through the sandbox (see [ADR-0023](docs/adr/0023-tenant-partitioned-storage-and-a-sandbox-that-serves-no-tenant-data.md)). Within a run a specialist's writes are further scoped to its own campaign, and an off-slug write is rejected (see [ADR-0006](docs/adr/0006-recoverable-tool-errors-and-slug-anchored-seeds.md)).
- **Quota** — a billable call is refused when the tenant's allowance is exhausted (see [ADR-0020](docs/adr/0020-usage-ledger-and-enforced-quota.md)).

## Repo map

**Tenant-Owned Documents** — reachable only through the `DocumentStore`, never by the read sandbox:

- `tenants/<tenant>/dna.md` — Brand DNA (input, human-authored). One per tenant; the old agency-shaped `customers/<name>/` collection is gone (see [ADR-0022](docs/adr/0022-brand-dna-and-the-overloaded-customer.md)).
- `tenants/<tenant>/campaigns/<slug>/` — per-campaign `goal.md` (input) + stage deliverables (output).
- `logs/<tenant>/<slug>/<run_id>.jsonl` — per-run traces.

**Code-Shipped Material** — identical for every tenant, which is what the read sandbox serves to agents:

- `knowledge/<discipline>/` — the Knowledge Library (stubs).
- `guardrails/*.md` — QA rubrics.
- `templates/` — Brand DNA and campaign-goal templates.
- `.claude/` — agents, rules, skills, permissions (the interactive configuration).

**Source** — not read by agents at all:

- `agent-harness/` — the LangGraph runtime enforcing the same governance.
- `web/` — the Next.js operator UI + BFF (see [ADR-0012](docs/adr/0012-nextjs-frontend-and-bff-in-monolith.md)).
- `contracts/` — the frozen OpenAPI contract between the frontend and the engine, its linter, and the mock server the frontend codes against (see [ADR-0017](docs/adr/0017-stages-and-lifecycle-are-separate-axes.md)).

Tenant-Owned Documents resolve through a `DocumentStore` port — filesystem and in-memory adapters exist today; Postgres joins as the production adapter, alongside checkpoints, guardrails, the knowledge library and the questionnaire (see [ADR-0014](docs/adr/0014-postgres-system-of-record-and-split-governance.md)). The eight rules, the pipeline definition and the specialist prompts stay as code-shipped markdown. The paths above describe the current filesystem layout, which the filesystem adapter serves for local development; the split between the two groups is the boundary the sandbox enforces (see [ADR-0023](docs/adr/0023-tenant-partitioned-storage-and-a-sandbox-that-serves-no-tenant-data.md)).

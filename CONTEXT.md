# Marketing OS

An AI-assisted **decision-making system** for small businesses and solo founders. It replicates the strategic process a professional marketer follows *before* assets are created; content is a downstream tool, never the goal. The system exists twice: as a `.claude/` agentic configuration (run interactively by Claude Code) and as the `agent-harness/` LangGraph application (the compiled runtime that enforces the same governance). See [docs/adr/](docs/adr/) for the decisions behind the current shape.

## Language

**Customer DNA**:
The stable, reusable, human-authored profile of a business and its customers (`customers/<name>/dna.md`). The single source of truth every recommendation is grounded in. Read-only to agents; authored once per customer, reused across campaigns.
_Avoid_: profile, brief, persona.

**Campaign Goal**:
The per-campaign business objective and success metrics (`campaigns/<slug>/goal.md`). The DNA is shared across campaigns; the goal is specific to one.
_Avoid_: objective doc, spec.

**Campaign Slug**:
The identifier for a single **campaign** — the durable thing. It names the campaign's directory (`campaigns/<slug>/`), so every input and deliverable for that campaign lives under it, and it keys the checkpoint thread that makes the campaign resumable. A specialist must use the campaign's slug verbatim; a write under any other slug is rejected as off-slug (see [ADR-0006](docs/adr/0006-recoverable-tool-errors-and-slug-anchored-seeds.md)).
_Avoid_: id, name, key, thread.

**Run**:
A single **execution attempt** of a campaign's pipeline, identified by a unique `run_id`. A campaign (slug) may accumulate many runs over its life — one per attempt — but **at most one run per slug may be active at a time** (a second concurrent run of the same slug is rejected). Each run has its own JSONL trace (`logs/<slug>/<run_id>.jsonl`) and, in the background-job model, its own status and cancellation handle. The slug names the campaign; the run_id names one attempt to advance it. A run's **status** is one of: **running** (executing now), **completed** (finished ok), **failed** (halted on an error), **cancelled** (stopped on operator/customer request), or **interrupted** (its process died — e.g. a restart — leaving a trace with no terminal summary). Cancelling a run **abandons** it: it is not resumed, and the next run of the slug starts clean. See [ADR-0010](docs/adr/0010-background-job-run-model.md) for the background-job model and [ADR-0009](docs/adr/0009-async-cancellable-pipeline-execution.md) for the cancellable async foundation it rests on.
_Avoid_: job (use for the background execution mechanism only), execution, session, thread.

**Marketing Director**:
The orchestrator (the `/new-campaign` skill / main session). Runs the DNA gate, sets the business goal and campaign strategy, and delegates to specialists in mandatory order. Never produces research, strategy, creative, or assets itself.
_Avoid_: coordinator, manager, supervisor.

**Specialist**:
One of the five subagents, each running in isolated context with restricted tools and a single output type: **market-research** (findings), **brand-strategy** (positioning/messaging/value prop), **creative-director** (creative briefs), **creative-asset-prompt** (generation prompts), **performance-marketing** (channels/KPIs/budget/optimization).
_Avoid_: worker, sub-agent (spelled with hyphen inconsistently), expert.

**Deliverable**:
The single markdown file a stage writes under `campaigns/<slug>/` (e.g. `research.md`, `brand-strategy.md`). A stage's deliverable existing on disk is the prerequisite for the next stage.
_Avoid_: output, artifact, document.

**Stage**:
One step of the mandatory pipeline, owned by exactly one role, producing exactly one deliverable. Stages never run out of order and never skip an upstream decision.
_Avoid_: step, phase, task.

**DNA Gate**:
The mandatory Stage 0 check: complete Customer DNA + complete Campaign Goal must both exist before any campaign work begins. On failure it lists what is missing and stops.
_Avoid_: precondition, validation.

**Guardrail** (a.k.a. **Rubric**):
A human-written QA standard (`guardrails/*.md`) a deliverable is scored against before the next stage may begin. `shared.md` applies to every deliverable; one file per stage adds stage-specific checks.
_Avoid_: check, test, lint.

**Knowledge Library**:
The central, citable store of expert frameworks by discipline (`knowledge/<discipline>/`). Read-only to agents in this version; agents cite which framework they applied. Currently stubs awaiting domain content.
_Avoid_: docs, references, wiki.

**Web Backend**:
The pluggable live-web capability (`WebSearchTool` port) granting the specialists that declare it — market-research and performance-marketing — `web_search`/`web_fetch` tools. Adapters: the default **NoopWebSearch**, which returns an honest "web search is not configured" message so runs stay grounded in the Customer DNA; **TavilyWebSearch**, the primary backend calling Tavily's JSON API (`/search` + `/extract`) over plain HTTP with no browser (see [ADR-0011](docs/adr/0011-tavily-primary-web-backend.md)); **PlaywrightWebSearch**, a browser-driven backend scraping DuckDuckGo (see [ADR-0007](docs/adr/0007-thread-confined-sync-playwright-backend.md)); and **GoogleWebSearch**, which subclasses it to scrape `google.com/search`, reusing the same browser lifecycle and `fetch`. The live capability is off by default and wired only when `MARKETING_OS_WEB=1` (see [ADR-0001](docs/adr/0001-ports-and-adapters-architecture.md)).
_Avoid_: search tool, web tool, scraper.

**Backend Fallback Chain** (`FallbackWebSearch`):
An ordered composition of web backends that is itself a `WebSearchTool`, so the graph wiring is unchanged. `search` tries each backend in priority order and falls through to the next on a recoverable `ToolError` or an empty result set; the final backend's outcome (result or raised error) surfaces unchanged, so a single configured backend behaves exactly as one backend alone. The order is set by `MARKETING_OS_WEB_BACKENDS` — a comma-separated, priority-ordered list of `tavily` / `google` / `duckduckgo` / `noop` (default `tavily,google,duckduckgo`, i.e. Tavily's JSON API first, with the Google → DuckDuckGo scrapers as fallback; see [ADR-0011](docs/adr/0011-tavily-primary-web-backend.md)). When `tavily` is in the list but `MARKETING_OS_TAVILY_API_KEY` is unset it is **skipped with a warning** (omitted from the chain) and the run proceeds on the scrapers. Recoverable failures — Tavily quota/5xx/network/timeout, or Google's anti-automation responses (consent interstitial, `/sorry/` CAPTCHA, zero-parse markup) — are raised as recoverable `ToolError`s so the chain moves on rather than crashing the run; a rejected Tavily key instead raises a terminal `ConfigError` that stops the run. (See [ADR-0008](docs/adr/0008-google-scraping-web-search-with-fallback-chain.md) for why the fallback engines are scraped rather than called via an official API.)
_Avoid_: retry chain, backend pool, load balancer.

**KPI tiers**:
The three levels every campaign must define, which ladder up to each other — **Business KPI** (revenue, leads, bookings, retention), **Marketing KPI** (CTR, CPC, CPM, conversion rate), **Creative KPI** (hook rate, watch time, engagement rate).
_Avoid_: metrics, goals (unqualified).

## The mandatory pipeline

Each stage requires the prior stage's deliverable to exist; no stage bypasses an upstream decision (`.claude/rules/decision-hierarchy.md`, `agent-harness/src/marketing_os/governance/pipeline.py`).

| Stage | Owner | Deliverable |
| --- | --- | --- |
| 0 — DNA Gate | Marketing Director | *(gate; no file)* |
| 1 — Research | market-research | `research.md` |
| 2 — Brand Strategy | brand-strategy | `brand-strategy.md` |
| 3 — Campaign Strategy | Marketing Director | `campaign-strategy.md` |
| 4 — Creative Brief | creative-director | `creative-brief.md` |
| 5 — Asset Prompts | creative-asset-prompt | `asset-prompts.md` |
| 6 — Performance Plan | performance-marketing | `performance-plan.md` |
| Launch → Analysis → Optimization | Marketing Director (+ performance-marketing) | *(operational loop)* |

## Hard constraints

- **DNA-grounded** — every recommendation traces to the Customer DNA or to research findings; generic filler is prohibited. If the DNA lacks what an agent needs, the agent says so rather than inventing.
- **Strategy before content** — creative assets are never generated before an approved strategy exists.
- **Upstream prerequisite** — a stage may not begin until the prior stage's deliverable exists.
- **QA budget** — each deliverable must pass its guardrail rubric within `MARKETING_OS_MAX_QA` revision rounds (default 3), or the run halts.
- **Write scope** — agents read anywhere under the repo but write only under `campaigns/**` (see [ADR-0005](docs/adr/0005-code-enforced-filesystem-sandbox.md)); within a run a specialist's writes are further scoped to its own campaign's directory `campaigns/<slug>/`, and an off-slug write is rejected (see [ADR-0006](docs/adr/0006-recoverable-tool-errors-and-slug-anchored-seeds.md)).

## Repo map

- `customers/<name>/dna.md` — Customer DNA (input, human-authored).
- `campaigns/<slug>/` — per-campaign `goal.md` (input) + stage deliverables (output).
- `knowledge/<discipline>/` — the Knowledge Library (stubs).
- `guardrails/*.md` — QA rubrics.
- `templates/` — Customer DNA and campaign-goal templates.
- `.claude/` — agents, rules, skills, permissions (the interactive configuration).
- `agent-harness/` — the LangGraph runtime enforcing the same governance.

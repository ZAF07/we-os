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
The identifier for a single campaign run. It names the campaign's directory (`campaigns/<slug>/`), so every input and deliverable for that campaign lives under it, and it identifies the run for resumption. A specialist must use the run's slug verbatim; a write under any other slug is rejected as off-slug (see [ADR-0006](docs/adr/0006-recoverable-tool-errors-and-slug-anchored-seeds.md)).
_Avoid_: id, name, key, thread.

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

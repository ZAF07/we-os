# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**Marketing OS** — an AI-assisted marketing operating system for small businesses and solo founders. It is a **decision-making system, not a content generator**: it replicates the strategic process professional marketers follow _before_ assets are created. The goal is always revenue growth; content/assets are downstream tools. See `README.md` for the full product vision.

The repository has two layers: the **interactive agentic system** configured under `.claude/` (markdown agents, rules, skills — no build step), and the **compiled harness** under `agent-harness/` — a LangGraph-based Python application (uv, ports-and-adapters) with its own `src/`, `tests/`, `Makefile`, and quality gates (`ruff`, `mypy`, `pytest`). Both layers read the same governance markdown (see ADR 0003).

## Directory map

| Path                           | Purpose                                                                                                                                    |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `.claude/agents/`              | The 5 specialist **subagents** (research, brand, creative, performance, asset-prompt). Each runs in its own context with restricted tools. |
| `.claude/skills/new-campaign/` | The **Marketing Director orchestrator** — entrypoint (`/new-campaign`) that runs the pipeline and delegates to specialists.                |
| `.claude/rules/`               | **Canonical governance**, loaded every session: the mandatory pipeline and operating principles.                                           |
| `.claude/settings.json`        | Permissions (read-only research tools pre-allowed).                                                                                        |
| `knowledge/`                   | Central domain-knowledge library, by discipline. Agents read frameworks from here.                                                         |
| `customers/<name>/dna.md`      | Reusable **Customer DNA** — the profile the agent grounds all work in. Human-authored; read-only to agents.                                |
| `campaigns/<slug>/`            | Per-campaign `goal.md` (input) + deliverables written by each pipeline stage. Writes here are pre-approved (no prompt).                    |
| `templates/`                   | Fill-in templates for Customer DNA and campaign goals.                                                                                     |
| `USAGE.md`                     | Operator guide: how to collect DNA, set the goal, and run the agent.                                                                       |
| `agent-harness/`               | Compiled LangGraph runtime — Python package (`src/marketing_os/`), tests, Makefile. Runs the same pipeline headlessly.                     |
| `CONTEXT.md`                   | Domain glossary and pipeline vocabulary — read before working in any area.                                                                 |
| `docs/adr/`                    | Architecture Decision Records — decisions not to re-litigate.                                                                              |
| `.scratch/<feature>/`          | Local issue tracker — PRDs and issues as markdown; the cross-session record of work (see `docs/agents/issue-tracker.md`).                  |

## Agent hierarchy → Claude Code mapping

| README role                       | Implemented as                   | Output                                      |
| --------------------------------- | -------------------------------- | ------------------------------------------- |
| Marketing Director (orchestrator) | `/new-campaign` skill            | Plan + delegation; never produces assets    |
| Market Research Agent             | `market-research` subagent       | Research findings only                      |
| Brand Strategy Agent              | `brand-strategy` subagent        | Positioning, messaging, value prop          |
| Creative Director Agent           | `creative-director` subagent     | Creative briefs                             |
| Performance Marketing Agent       | `performance-marketing` subagent | Channels, KPIs, budget, optimization        |
| Creative Asset Prompt Agent       | `creative-asset-prompt` subagent | Generation prompts; strictly follows briefs |

## Governance

The mandatory decision pipeline and the non-negotiable rules are the canonical source of truth in `.claude/rules/` (`decision-hierarchy.md`, `operating-principles.md`, `customer-dna.md`) — loaded into every session. The core constraints: **a complete Customer DNA gates all work** (no research/strategy/creative/assets until `customers/<name>/dna.md` is complete — see `customer-dna.md`); **strategy before content; never generate assets before strategy exists; no stage bypasses an upstream decision.** Each subagent also restates its own key guardrail inline, since subagents run in isolated context and don't inherit project rules.

## Where domain knowledge goes

Expert marketing knowledge lives in `knowledge/<discipline>/` as individual `.md` files, cited by the matching agent. The skeleton ships with stubs and `TODO` markers; fill these in rather than embedding expertise inside agent prompts. See `knowledge/README.md`.

In this version `knowledge/` is **read-only** to agents. A planned future capability — agents writing back the reusable frameworks they discover — is documented (and intentionally left inactive) under "Future capability" in `knowledge/README.md`.

## Coding standards

- Type-annotate all public functions; `mypy` must pass on `src/`.
- Use absolute path imports instead of relative
- Use UV for package and virtual env management
- Keep functions focused; prefer pure functions and dependency injection over globals.
- Function and variable names MUST be clear and describe what they do or hold.
- All methods _MUST_ have _google-style docstrings_ describing in concise manner what the method does, what parameters it takes and what it returns
- No inline comments. If comments are absolutely needed, then put them in google style docstrings in the function.
- Match the style of surrounding code — naming, comment density, structure.
- No secrets, API keys, or tokens in code or commits. Read them via `config.py`/`.env`.
- New code comes with tests. Don't mark a task done until `pytest`, `ruff`, and `mypy`
  pass — and say so explicitly, with output, if any of them fail.
- Follow the ports-and-adapters pattern (https://8thlight.com/insights/a-color-coded-guide-to-ports-and-adapters)

---

## How I want you to work (process)

- **Plan before large changes.** For anything non-trivial, outline the approach first.
- **Small, reviewable steps.** Prefer incremental edits over sweeping rewrites.
- **Verify, don't assume.** Run the relevant command and report the real result.
- **Ask when genuinely blocked** on a decision only I can make; otherwise pick the
  sensible default, state it, and proceed.
- **Don't stage, commit or push** unless I ask.

---

## Development workflow (router)

Every piece of work — feature, refactor, or bug — gets an issue file in `.scratch/<feature>/issues/` **before** code changes. The issue file is the cross-session anchor: status, decisions, and blockers live there, not in chat history.

**New feature:**

1. `/grill-with-docs` — sharpen the idea; ADRs and `CONTEXT.md` updates land as decisions are made. (Skippable for small, well-understood work.)
2. `/to-prd` — synthesize the conversation into `.scratch/<feature>/PRD.md`.
3. `/to-issues` — break into tracer-bullet vertical slices with `Blocked by:` dependencies.
4. Per issue, on a branch: `/implement <issue path>` — TDD at agreed seams, quality gates, then `/code-review`.
5. `/verify` (or `/run`) — confirm the change actually works in the running app, not just that tests pass. Skipping this is how green tests ship broken behaviour.
6. `/post-implement` — verify acceptance criteria with evidence, mark `completed`, archive. Then `/domain-modeling` if the change moved the domain model (new terms, decisions) so `CONTEXT.md`/ADRs don't drift.

**Improve existing code:** `/simplify` for diff-scoped cleanup; `/improve-codebase-architecture` (with `/codebase-design` vocabulary) for structural work. Once scoped, funnel into an issue and follow steps 4–6 above — refactors get issues too, and get verified too.

**Debugging:** `/file-bug` to record it as an issue → `/diagnosing-bugs` (build a tight pass/fail feedback loop before touching code) → fix test-first with `/tdd` → `/verify` the fix in the running system → `/code-review` → `/post-implement`, recording the confirmed hypothesis in the archived issue.

**What counts as a bug (important):** a bug is a defect in **already-implemented, shipped code** — the running system crashes, throws, or logs an error when exercised. Those get filed with `/file-bug`. A defect in code being written *right now* (a broken function in the current diff, a failing test you just introduced) is **not** filed — fix it in place as part of finishing that work. When the user mentions a bug, this is the distinction to apply before reaching for `/file-bug`.

**Session ritual:**

- **Start**: run `/triage` ("show me what needs attention") to re-orient on in-flight work. When the user asks "what's in flight?" or "where were we?", this is the answer.
- **End, work complete**: `/post-implement`, then the user commits the `.scratch/` status change (commit message convention: "updated tasks status").
- **End, mid-task**: append a status note under `## Comments` in the active issue file — where things stand, what's next, any open questions.

---

## Definition of done

A task is done when:

1. Code compiles / imports, and the change is **verified in the running app** (via `/verify` or `/run`) — not just green in tests.
2. `uv run ruff check .`, `uv run ruff format`, `uv run mypy src`, and `uv run pytest` all pass.
3. New behavior has tests; for a bug fix, a test that was red before the fix and is green after.
4. Acceptance criteria on the issue are checked off with evidence, and you've reported what you changed and any caveats plainly.

---

## Agent skills

### Issue tracker

Issues and PRDs are tracked as local markdown files under `.scratch/<feature>/`; external PRs are not a triage surface. See `docs/agents/issue-tracker.md`.

### Triage labels

Uses the five canonical triage roles with default strings (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`), recorded as a `Status:` line in each issue file. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

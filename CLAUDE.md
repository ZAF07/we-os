# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**Marketing OS** — an AI-assisted marketing operating system for small businesses and solo founders. It is a **decision-making system, not a content generator**: it replicates the strategic process professional marketers follow *before* assets are created. The goal is always revenue growth; content/assets are downstream tools. See `README.md` for the full product vision.

There is no application code, build, or test suite. The repository *is* an agentic system configured under `.claude/`.

## Directory map

| Path | Purpose |
|---|---|
| `.claude/agents/` | The 5 specialist **subagents** (research, brand, creative, performance, asset-prompt). Each runs in its own context with restricted tools. |
| `.claude/skills/new-campaign/` | The **Marketing Director orchestrator** — entrypoint (`/new-campaign`) that runs the pipeline and delegates to specialists. |
| `.claude/rules/` | **Canonical governance**, loaded every session: the mandatory pipeline and operating principles. |
| `.claude/settings.json` | Permissions (read-only research tools pre-allowed). |
| `knowledge/` | Central domain-knowledge library, by discipline. Agents read frameworks from here. |
| `customers/<name>/dna.md` | Reusable **Customer DNA** — the profile the agent grounds all work in. Human-authored; read-only to agents. |
| `campaigns/<slug>/` | Per-campaign `goal.md` (input) + deliverables written by each pipeline stage. Writes here are pre-approved (no prompt). |
| `templates/` | Fill-in templates for Customer DNA and campaign goals. |
| `USAGE.md` | Operator guide: how to collect DNA, set the goal, and run the agent. |

## Agent hierarchy → Claude Code mapping

| README role | Implemented as | Output |
|---|---|---|
| Marketing Director (orchestrator) | `/new-campaign` skill | Plan + delegation; never produces assets |
| Market Research Agent | `market-research` subagent | Research findings only |
| Brand Strategy Agent | `brand-strategy` subagent | Positioning, messaging, value prop |
| Creative Director Agent | `creative-director` subagent | Creative briefs |
| Performance Marketing Agent | `performance-marketing` subagent | Channels, KPIs, budget, optimization |
| Creative Asset Prompt Agent | `creative-asset-prompt` subagent | Generation prompts; strictly follows briefs |

## Governance

The mandatory decision pipeline and the non-negotiable rules are the canonical source of truth in `.claude/rules/` (`decision-hierarchy.md`, `operating-principles.md`, `customer-dna.md`) — loaded into every session. The core constraints: **a complete Customer DNA gates all work** (no research/strategy/creative/assets until `customers/<name>/dna.md` is complete — see `customer-dna.md`); **strategy before content; never generate assets before strategy exists; no stage bypasses an upstream decision.** Each subagent also restates its own key guardrail inline, since subagents run in isolated context and don't inherit project rules.

## Where domain knowledge goes

Expert marketing knowledge lives in `knowledge/<discipline>/` as individual `.md` files, cited by the matching agent. The skeleton ships with stubs and `TODO` markers; fill these in rather than embedding expertise inside agent prompts. See `knowledge/README.md`.

In this version `knowledge/` is **read-only** to agents. A planned future capability — agents writing back the reusable frameworks they discover — is documented (and intentionally left inactive) under "Future capability" in `knowledge/README.md`.

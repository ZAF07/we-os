# Marketing OS — Agent Harness

A provider-agnostic Python harness that runs the Marketing OS decision pipeline
over **direct LLM API access**. It reproduces the governance encoded in the
repo's `.claude/` configuration — the Customer DNA gate, the mandatory decision
pipeline, the five specialist agents, and a per-stage self-critique loop — as a
library, a CLI, and an HTTP API you can build a SaaS on.

It reads its prompts and rules from the repo at runtime (single source of truth):
`.claude/agents/*.md` are the specialist system prompts, `.claude/rules/*.md` are
the governance preamble, `templates/*.md` define the gate, `guardrails/*.md` are
the QA rubrics, and `knowledge/**` is what the agents cite. Editing that markdown
changes behavior with no code change. The harness writes only under
`campaigns/<slug>/`, exactly like the Claude Code config.

## Install

```bash
cd agent-harness
python3 -m venv .venv && . .venv/bin/activate
pip install -e .                # core: pydantic, pyyaml, httpx, fastapi, uvicorn
pip install -e '.[openai]'      # DeepSeek (primary) + OpenAI adapters
pip install -e '.[anthropic]'   # Claude adapter
pip install -e '.[playwright]'  # to implement the Playwright web-search stub
pip install -e '.[dev]'         # pytest
```

## Configure (environment)

The active provider and its connection details are pure config:

| Var | Default | Notes |
|---|---|---|
| `MARKETING_OS_PROVIDER` | `deepseek` | `deepseek` \| `anthropic` \| `openai` |
| `MARKETING_OS_ROOT` | auto-discovered | repo dir containing `.claude/` |
| `DEEPSEEK_API_KEY` / `DEEPSEEK_MODEL` / `DEEPSEEK_BASE_URL` | — / `deepseek-v4-pro` / `https://api.deepseek.com/v1` | **CONFIRM** the model id + base URL for your account |
| `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` | — / `claude-opus-4-8` | Claude adapter |
| `OPENAI_API_KEY` / `OPENAI_MODEL` / `OPENAI_BASE_URL` | — / *(required)* / — | OpenAI adapter |
| `MARKETING_OS_MAX_STEPS` | `20` | tool-use steps per agent |
| `MARKETING_OS_MAX_QA` | `3` | self-critique iterations per stage |
| `MARKETING_OS_STREAM` | `1` | token streaming |

> The DeepSeek model id and base URL are **placeholders to confirm** — set the
> env vars to the exact values for your account. Nothing about the endpoint is
> hard-coded.

## CLI

```bash
marketing-os agents                 # list specialists + their tool grants
marketing-os check <customer>       # run only the Stage 0 gate
marketing-os new-campaign <customer> [--slug S] [--stage research] [--provider anthropic] [--no-stream]
```

`new-campaign` runs the gate, then the pipeline (research → brand-strategy →
campaign-strategy → creative-brief → asset-prompts → performance-plan), printing
each stage and its QA iterations, writing deliverables under `campaigns/<slug>/`.

## HTTP API

```bash
uvicorn marketing_os.api.app:app --reload
```

- `POST /campaigns` `{customer, slug?}` — scaffold `goal.md` from the template
- `GET  /campaigns/{slug}/gate?customer=` — Stage 0 report
- `POST /campaigns/{slug}/run` `{customer, stage?}` — run the pipeline/one stage
- `GET  /campaigns/{slug}/deliverables` — list written deliverables
- `GET  /campaigns/{slug}/stream?customer=&stage=` — SSE progress

## Library

```python
from marketing_os import load_settings, MarketingDirector

director = MarketingDirector(load_settings())
result = director.run_campaign("coast-coffee")
for s in result.stages:
    print(s.stage, s.deliverable_path, "QA:", s.qa_iterations)
```

## Architecture (extension points)

```
providers/   adapter pattern — DeepSeek (primary), Anthropic, OpenAI behind one
             Provider interface. Add a backend: one adapter + register().
loop/        agent-loop SCAFFOLD — AgentLoop ABC with `# SEAM (fill in)` hooks +
             a working DefaultToolUseLoop. Subclass to add budget caps, planning,
             human-in-the-loop approval, parallel tools, etc.
tools/       filesystem (scoped: write only campaigns/**), pluggable web search.
             websearch_playwright.py is a STUB to fill in for browser search.
agents/      loads .claude/agents/*.md -> AgentSpec; Specialist runs one agent.
governance/  rules preamble, Stage 0 gate, the pipeline, and the QA reviewer.
orchestrator MarketingDirector: gate -> pipeline -> specialist + QA + approval.
```

**Self-critique loop:** after a specialist writes its deliverable, the reviewer
scores it against `guardrails/<stage>.md` + `guardrails/shared.md` + the operating
principles and returns structured discrepancies; the specialist revises until the
verdict passes or `MARKETING_OS_MAX_QA` is hit. Unresolved discrepancies block the
stage (override via the `approval` hook on `MarketingDirector`).

## Tests

```bash
pytest                  # offline; uses a deterministic FakeProvider (no network)
```

Covers the gate (incl. multi-line field values), the agent loader, pipeline
gating, the QA loop (pass/fail/unparseable), and the default tool-use loop
(dispatch, refusal, max-steps).

### Live checks (need a real key)

```bash
export DEEPSEEK_API_KEY=...        # or ANTHROPIC_API_KEY + --provider anthropic
marketing-os new-campaign coast-coffee --slug coast-coffee-test   # throwaway slug
# Provider-swap proof: run the same stage under two adapters
marketing-os new-campaign coast-coffee --slug t1 --stage research
marketing-os new-campaign coast-coffee --slug t2 --stage research --provider anthropic
```

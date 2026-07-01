# Marketing OS — Agent Harness

A **LangGraph** application that runs the Marketing OS decision pipeline. It
reproduces the governance encoded in the repo's `.claude/` configuration — the
Customer DNA gate, the mandatory decision pipeline, the specialist agents, and a
per-stage self-critique loop — as a compiled `StateGraph`, wrapped by a CLI and an
HTTP API you can build a SaaS on.

It reads its prompts and rules from the repo at runtime (single source of truth):
`.claude/agents/*.md` are the specialist system prompts, `.claude/rules/*.md` are
the governance preamble, `templates/*.md` define the gate, `guardrails/*.md` are
the QA rubrics, and `knowledge/**` is what the agents cite. Editing that markdown
changes behavior with no code change. The harness writes only under
`campaigns/<slug>/`.

## For domain experts — where the knowledge lives

**Why:** the LLM agents are steered entirely by markdown you write. These files are
the single source of truth the harness loads at runtime — editing them changes what
the agents do with **no code change**. This is how a human encodes professional
judgment, guardrails, and customer truth into the system. Write them well and the
output is sharp and grounded; leave them thin and the output is generic.

**What to write, what it makes the agents do, and where:**

| Surface | What to write | What it makes the agents do / not do | Where |
| --- | --- | --- | --- |
| **Customer DNA** | The customer's business truth — every Required field, no `<placeholders>`: who they are, what they sell, their customers, differentiation, competitors, voice, hard constraints. | Grounds every recommendation. The **pipeline will not start** until it is complete (Stage 0 gate); agents must cite it and may **not** invent what it omits. | `customers/<name>/dna.md` (copy from `templates/customer-dna.md`) |
| **Campaign goal** | The objective, all three KPI tiers (business / marketing / creative), budget, timeframe, and any offer. | Sets what the campaign optimizes toward; every decision must tie back to it. The gate blocks the run until it is complete. | `campaigns/<slug>/goal.md` (copy from `templates/campaign-goal.md`) |
| **QA rubrics (guardrails)** | Concrete, checkable acceptance criteria per stage — e.g. "names actual competitors and how they position", not "good research". | This is exactly what the QA reviewer grades each deliverable against. Sharp rubrics → the specialist iterates until it passes; a stage **will not advance** until it does (within `MARKETING_OS_MAX_QA`). The reviewer can only enforce what you write. | `guardrails/shared.md` (cross-cutting) + `guardrails/<stage>.md` |
| **Governance rules** | The non-negotiable principles and the mandatory pipeline order. | Prepended to every agent's system prompt — the hard rules: strategy before content, no stage bypasses an upstream one, the DNA gate. | `.claude/rules/*.md` |
| **Agent role definitions** | Each specialist's remit, guardrails, and its granted tools (frontmatter `tools:`). | Define what each specialist does and must **not** do (e.g. research outputs findings only, never strategy), and what it may read / write / search. | `.claude/agents/<name>.md` |
| **Knowledge base** | Your expert frameworks and playbooks, by discipline (positioning models, channel playbooks, research methods). | Agents cite these to ground work in real frameworks instead of generic knowledge. Read-only to agents. | `knowledge/<discipline>/*.md` |

Start with the Customer DNA and the campaign goal (the gate needs both), then sharpen
the `guardrails/` rubrics to your professional bar — those two levers move quality the most.

## Install (UV)

```bash
cd agent-harness
uv sync                                   # core deps into .venv
uv sync --extra anthropic --extra openai  # optional alternate providers
uv sync --extra postgres                  # PostgresSaver for cross-process resume
```

The primary provider is **DeepSeek** via `langchain-deepseek`; Anthropic and
OpenAI are swappable through `init_chat_model`.

## Configure (environment)

| Var                                                         | Default                           | Notes                                   |
| ----------------------------------------------------------- | --------------------------------- | --------------------------------------- |
| `MARKETING_OS_PROVIDER`                                     | `deepseek`                        | `deepseek` \| `anthropic` \| `openai`   |
| `MARKETING_OS_ROOT`                                         | auto-discovered                   | repo dir containing `.claude/`          |
| `DEEPSEEK_API_KEY` / `DEEPSEEK_MODEL` / `DEEPSEEK_BASE_URL` | — / `deepseek-chat` / SDK default | confirm the model id for your account   |
| `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL`                     | — / `claude-opus-4-8`             | Anthropic provider                      |
| `OPENAI_API_KEY` / `OPENAI_MODEL` / `OPENAI_BASE_URL`       | — / _(required)_ / —              | OpenAI provider                         |
| `MARKETING_OS_REVIEWER_MODEL`                               | —                                 | optional cheaper model for the QA judge |
| `MARKETING_OS_MAX_STEPS`                                    | `20`                              | tool-use steps per specialist           |
| `MARKETING_OS_MAX_QA`                                       | `3`                               | self-critique iterations per stage      |
| `MARKETING_OS_REVIEWER_THINKING`                          | `0`                               | keep the QA reviewer in thinking mode (off: DeepSeek V4 needs non-thinking for structured output) |
| `MARKETING_OS_LOG_LEVEL`                                   | `INFO`                            | console log level (`DEBUG` for detail)  |
| `MARKETING_OS_RUN_LOGS`                                    | `1`                               | write a per-run JSONL trace to `logs/`  |
| `LANGSMITH_TRACING` / `LANGCHAIN_API_KEY`                  | —                                 | enable LangSmith deep tracing (opt-in)  |

## CLI

```bash
uv run marketing-os agents                 # list specialists + their tool grants
uv run marketing-os check <customer>       # run only the Stage 0 gate
uv run marketing-os new-campaign <customer> [--slug S] [--stage research] [--provider anthropic]
```

`new-campaign` runs the gate, then the pipeline (research → brand-strategy →
campaign-strategy → creative-brief → asset-prompts → performance-plan), streaming
each stage and its QA iterations and writing deliverables under `campaigns/<slug>/`.

## HTTP API

```bash
uv run uvicorn marketing_os.entrypoints.api.app:app --reload
```

- `POST /campaigns` `{customer, slug?}` — scaffold `goal.md` from the template
- `GET  /campaigns/{slug}/gate?customer=` — Stage 0 report
- `POST /campaigns/{slug}/run` `{customer, stage?}` — run the pipeline/one stage
- `GET  /campaigns/{slug}/deliverables` — list written deliverables
- `GET  /campaigns/{slug}/stream?customer=&stage=` — SSE progress (native `astream`)
- `GET  /campaigns/{slug}/runs` — list past run-log traces
- `GET  /campaigns/{slug}/runs/{run_id}` — fetch one run's parsed trace

## Observability

Every run is observable three ways, all driven off the graph's semantic events:

- **Live console logs.** Each stage transition and QA verdict is logged (stdlib
  `logging`) as it happens — for `/run` and `/stream` alike. Set
  `MARKETING_OS_LOG_LEVEL=DEBUG` for more detail. A failing QA review logs the
  reviewer summary and each violated rubric point, so you see *why* live.
- **Persistent per-run trace.** Every run writes `logs/<slug>/<run-id>.jsonl` — one
  line per event plus a final `run.summary` (outcome, per-stage results, usage).
  Inspect a finished or failed run afterwards, or fetch it via the `runs` endpoints.
  Toggle with `MARKETING_OS_RUN_LOGS=0`.
- **LangSmith (deep traces).** Set `LANGSMITH_TRACING=true` and `LANGCHAIN_API_KEY`
  to trace every prompt, tool call, and model response under project `marketing-os`;
  runs and stages appear as named spans (`specialist:research`, `review:research`).

On a QA failure the `/run` response now carries the structured reason
(`stage`, `summary`, `discrepancies`, `run_log`) instead of a bare message, and the
rejected deliverable is still on disk under `campaigns/<slug>/` for inspection.

## Library

```python
from marketing_os import load_settings, build_campaign_graph

settings = load_settings()
graph = build_campaign_graph(settings)
state = graph.invoke(
    {"customer": "coast-coffee", "slug": "coast-coffee"},
    config={"configurable": {"thread_id": "coast-coffee"}},
)
for record in state["results"]:
    print(record["stage"], record["deliverable_path"], "QA:", record["qa_iterations"])
```

Runs are keyed by `thread_id`, so re-invoking the same slug resumes from the last
checkpoint. `graph.runner.run_campaign` / `astream_campaign` wrap this with typed
results and error mapping.

## Architecture

The pipeline is a **mandatory, deterministic sequence**, so it is a hand-built
`StateGraph` (not a supervisor). The layout is ports-and-adapters:

```
schemas.py    domain models (Pydantic): ReviewVerdict, StageResult, CampaignResult
ports.py      the Reviewer port (the model/tool ports are LangChain's own types)
config.py     env-driven Settings + per-provider / per-role model resolution
governance/   framework-free core: rules preamble, Stage 0 gate, pipeline, rubric
agents/       loads .claude/agents/*.md -> AgentSpec; build_specialist -> create_agent
adapters/     driven adapters — models (chat model), tools (@tool + sandbox),
              review (LLM-as-judge, structured output), persistence (checkpointer)
graph/        state (TypedDict + reducers), nodes, graph assembly, runner
entrypoints/  driving adapters — the CLI and the FastAPI app
```

**Graph shape.** One flat graph built from `PIPELINE`: a `gate` node, then per
stage an `enter → specialist → review` trio. The gate short-circuits to the end on
failure. Each stage's specialist is a `create_agent` react loop; the review node
verifies the deliverable was saved (forcing a save-retry if not), scores it against
`guardrails/<stage>.md` + `guardrails/shared.md` + the operating principles, and
either advances, loops back for a revision, or fails once the QA budget is spent.

## Tests & checks

```bash
uv run pytest          # offline; scripted fake chat model + fake reviewer (no network)
uv run ruff format
uv run ruff check .
uv run mypy src
```

`tests/test_graph.py` exercises the full graph: gate halt, the QA revise loop,
save-retry, budget exhaustion, prerequisite halt, and a full six-stage advance.

### Live run (needs a real key)

```bash
export DEEPSEEK_API_KEY=...
export MARKETING_OS_REVIEWER_MODEL=...
uv run marketing-os new-campaign coast-coffee --slug coast-coffee-test --stage research
```

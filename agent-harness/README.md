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

| Var | Default | Notes |
|---|---|---|
| `MARKETING_OS_PROVIDER` | `deepseek` | `deepseek` \| `anthropic` \| `openai` |
| `MARKETING_OS_ROOT` | auto-discovered | repo dir containing `.claude/` |
| `DEEPSEEK_API_KEY` / `DEEPSEEK_MODEL` / `DEEPSEEK_BASE_URL` | — / `deepseek-chat` / SDK default | confirm the model id for your account |
| `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` | — / `claude-opus-4-8` | Anthropic provider |
| `OPENAI_API_KEY` / `OPENAI_MODEL` / `OPENAI_BASE_URL` | — / *(required)* / — | OpenAI provider |
| `MARKETING_OS_REVIEWER_MODEL` | — | optional cheaper model for the QA judge |
| `MARKETING_OS_MAX_STEPS` | `20` | tool-use steps per specialist |
| `MARKETING_OS_MAX_QA` | `3` | self-critique iterations per stage |

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
uv run marketing-os new-campaign coast-coffee --slug coast-coffee-test --stage research
```

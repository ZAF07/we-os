# Marketing OS — ADK Agent Harness

A coordinator-led, multi-agent marketing system built on **Google ADK**. One
coordinator runs a 9-stage specialist pipeline; agents have real tools (file I/O
and a **real Playwright web browser**), per-agent-configurable tool access and
human checks, a two-tier guardrail system, persistent cross-task memory, and
strict per-stage typed deliverables. Driven from a CLI and a FastAPI service.

```
User request
 → Intake
 → refine loop(                                            ← iterates until the Evaluator passes
      Research → Brand strategy → Campaign strategy →
      Creative brief → Asset prompts → Performance plan → Evaluator → gate )
 → [Human approval]      (optional; off by default)
 → Execution   → Performance monitoring
```

The six stages inside the refine loop are the canonical `.claude` pipeline, in
order (research first), writing `research.md`, `brand-strategy.md`,
`campaign-strategy.md`, `creative-brief.md`, `asset-prompts.md`,
`performance-plan.md`. The loop re-runs the whole pipeline until the Evaluator
passes, so each stage can incorporate the Evaluator's feedback.

**Google Gemini is the primary model** (native to ADK); DeepSeek/Claude/OpenAI
are a config switch (via ADK's LiteLLM wrapper). Governance (the Customer DNA gate and the
`.claude/rules/*.md` preamble) and the editable `guardrails/*.md` rubrics are
reused from the repo unchanged; deliverables are written only under
`campaigns/<slug>/`.

## Install (uv)

```bash
cd agent-harness
uv sync --extra dev            # creates .venv, installs google-adk, litellm, playwright, fastapi…
uv run playwright install chromium
```

## Configure (environment)

| Var | Default | Notes |
|---|---|---|
| `MARKETING_OS_PROVIDER` | `gemini` | `gemini` \| `deepseek` \| `anthropic` \| `openai` |
| `GOOGLE_API_KEY` / `GOOGLE_MODEL` | — / `gemini-2.5-flash` | **Primary.** AI Studio key; native to ADK. **Confirm/override the model id.** For Vertex instead, set `GOOGLE_GENAI_USE_VERTEXAI=TRUE` + `GOOGLE_CLOUD_PROJECT`/`GOOGLE_CLOUD_LOCATION` (no API key). |
| `DEEPSEEK_API_KEY` / `DEEPSEEK_MODEL` | — / `deepseek/deepseek-chat` | DeepSeek via LiteLLM |
| `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` | — / `anthropic/claude-opus-4-8` | Claude via LiteLLM |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | — / `openai/gpt-4o` | OpenAI via LiteLLM |
| `MARKETING_OS_ROOT` | auto | Repo dir containing `.claude/` |
| `MARKETING_OS_MAX_EVAL` | `3` | Evaluator refine-loop iterations |
| `MARKETING_OS_MEMORY_DB` | `<root>/.marketing_os/memory.sqlite3` | Cross-task memory store |

## CLI

```bash
uv run marketing-os agents                 # list agents + their tool grants
uv run marketing-os check <customer>        # Stage-0 gate only
uv run marketing-os new-campaign <customer> [--slug S] [--provider P] [--show]
```

`new-campaign` runs the gate then the full pipeline, printing each step's decision
envelope and any guardrail flags. If an agent requests human approval, the CLI
prompts inline and resumes.

**Runs are resumable.** State is checkpointed to `campaigns/<slug>/.run_state.json`
after each stage; re-running resumes where it stopped (transient model errors like
a Gemini 503 auto-retry and resume in-process). Use `--fresh` to start over.

## API

```bash
uv run uvicorn marketing_os.api.app:app --reload
```

See `USAGE.md` for the full endpoint guide (campaign scaffold, gate, background
run, SSE progress, and the `POST /approvals/{id}` resume).

## Architecture

```
marketing_os/
  config.py        settings, provider/model resolution, paths, memory + loop limits
  model.py         build the ADK model (LiteLlm) from config — provider switch
  schemas.py       DecisionEnvelope (per-step) + strict per-stage deliverable schemas
  agents/
    prompts/*.md   role instruction bodies (intake … performance)
    agents.yaml    PER-AGENT tools + confirm + human_check; approval-gate switch
    registry.py    load agents.yaml -> typed configs
    builder.py     per stage: worker (tools) + formatter (output_schema); evaluator; escalation gate
  tools/
    browser.py     REAL Playwright (async) browser: open/read/links/click/tabs/switch/back
    filesystem.py  read/write/list/search, write-scoped to campaigns/**
    memory_tools.py recall (search long-term) / remember (durable note)
    approval.py    request_human_approval (LongRunningFunctionTool → pause/resume)
    __init__.py    build_tools: maps an agent's allowlist -> concrete ADK tools
  guardrails/
    hard.py        NON-EDITABLE floor (code) + cheap scan_output checks
    callbacks.py   after_model (capture envelope + scan), before_tool (log) — the enforcement points
    review.py      load editable repo-root guardrails/*.md rubrics for the Evaluator
  memory/service.py  FileBackedMemoryService(BaseMemoryService) — SQLite, cross-task recall
  governance/
    gate.py        Stage-0 Customer DNA + goal gate (unchanged logic)
    rules.py       load .claude/rules/*.md into every agent's preamble
  pipeline.py      build_coordinator: the 9-stage ADK graph (Sequential + Loop)
  orchestrator.py  MarketingDirector: gate → Runner(session+memory) → run + approval resume → persist
  cli.py  api/app.py   the two surfaces
```

## How the pieces realize the requirements

- **Coordinator + sub-agents** — `SequentialAgent` coordinator; the Evaluator sits
  in a `LoopAgent` that re-runs strategy→creative→media until it passes.
- **Tools** — ADK function tools; the browser is a real stateful Playwright session.
- **Per-agent config** — `agents.yaml` is authoritative: a capability not listed is
  never handed to the agent. `confirm:` gates a tool behind human confirmation;
  `human_check:` attaches the approval tool.
- **Two-tier guardrails** — non-editable `hard.py` (injected into every prompt +
  scanned via callbacks) and editable `guardrails/*.md` rubrics (scored by the Evaluator).
- **Self-check each step** — every worker thinks in the `DecisionEnvelope` schema;
  `after_model_callback` captures it and scans against the hard floor; the Evaluator
  loop is the formal gate.
- **Memory** — session state shares deliverables downstream in a run; the file-backed
  `MemoryService` + `recall` tool retrieve prior campaigns across runs.
- **Typed output** — each stage's formatter emits a strict Pydantic deliverable.

## Tests

```bash
uv run pytest -q
```

Offline (no network, no key): gate, schemas, per-agent tool allowlist + confirmation
wiring, guardrail scan + envelope capture, the **real browser** against local pages,
and ADK graph assembly + the escalation gate. A live end-to-end run needs a real
`DEEPSEEK_API_KEY` — see `USAGE.md`.

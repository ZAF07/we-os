# Usage — Marketing OS as an API

**What** this is: an HTTP + library interface to the Marketing OS agent pipeline.
**Why** use it as an API: so your SaaS frontend (or another service) can start
campaigns, watch progress, and fetch deliverables without embedding the engine.
**How** it works: every request runs the same governance the CLI does — Stage 0
gate → mandatory pipeline → specialist agent + QA self-critique per stage.

---

## 1. Run the service

```bash
cd agent-harness
uv sync                                    # install into .venv
export DEEPSEEK_API_KEY=...                 # primary provider key
export DEEPSEEK_MODEL=deepseek-chat         # confirm the exact id for your account
uv run uvicorn marketing_os.entrypoints.api.app:app --reload  # http://127.0.0.1:8000
```

Provider is config-only: set `MARKETING_OS_PROVIDER=anthropic` (+ `ANTHROPIC_API_KEY`)
or `openai` to swap backends with no code change.

---

## 2. The lifecycle (what → why → how)

| Step | What | Why | Endpoint |
|---|---|---|---|
| 1 | Scaffold a campaign | create `campaigns/<slug>/goal.md` from the template to fill in | `POST /campaigns` |
| 2 | Check the gate | confirm DNA + goal are complete before spending tokens | `GET /campaigns/{slug}/gate` |
| 3 | Run the pipeline | produce the deliverables (research → … → performance plan) | `POST /campaigns/{slug}/run` or `GET …/stream` |
| 4 | Fetch results | read the written deliverables | `GET /campaigns/{slug}/deliverables` |

Customer DNA (`customers/<name>/dna.md`) is authored once by a human and reused
across campaigns — the API does not create it. If it's missing/incomplete the
gate fails and `run` returns `409`.

---

## 3. Endpoints

### `GET /health`
```json
{ "status": "ok", "provider": "deepseek", "root": "/…/we-os" }
```

### `POST /campaigns`  — scaffold a goal file
```bash
curl -X POST localhost:8000/campaigns -H 'content-type: application/json' \
  -d '{"customer":"coast-coffee","slug":"coast-spring"}'
```
```json
{ "slug":"coast-spring","customer":"coast-coffee",
  "goal_created_from_template": true,
  "gate_ok": false, "gate_issues": ["Goal: placeholder/empty Required field: 'Timeframe'", "…"] }
```
**Why** `gate_ok:false` here is expected — the freshly-copied `goal.md` still has
`<…>` placeholders. Fill them in, then re-check.

### `GET /campaigns/{slug}/gate?customer=<name>`
```json
{ "ok": true, "issues": [] }
```
**Why**: the Stage 0 gate — DNA + goal completeness. `run` enforces this too;
call it first to give users a precise "fix these fields" list.

### `POST /campaigns/{slug}/run`  — run the pipeline (blocking)
```bash
curl -X POST localhost:8000/campaigns/coast-spring/run -H 'content-type: application/json' \
  -d '{"customer":"coast-coffee"}'            # add "stage":"research" to run one stage
```
```json
{ "customer":"coast-coffee","slug":"coast-spring",
  "stages":[
    { "stage":"research","deliverable_path":"campaigns/coast-spring/research.md",
      "qa_iterations":1,"save_retries":0,"approved":true,
      "verdict":{"passed":true,"summary":"…","discrepancies":[]} }
    /* … one per stage … */ ],
  "usage":{"input_tokens":80000,"output_tokens":21000,
           "cache_read_input_tokens":0,"cache_creation_input_tokens":0} }
```
**Errors:** `409` = gate failed (fix DNA/goal); `422` = pipeline/guardrail block
(e.g. a stage's QA discrepancies stayed unresolved past the iteration budget).
Token usage is aggregated for the whole run via LangChain's usage callback.

### `GET /campaigns/{slug}/stream?customer=<name>[&stage=<key>]`  — SSE progress
**Why**: the pipeline is long-running; stream stage/QA events to a UI instead of
blocking. Server-Sent Events, one JSON object per `data:` line:
```
data: {"event":"gate.passed","customer":"coast-coffee","slug":"coast-spring"}
data: {"event":"stage.start","stage":"research","agent":"market-research"}
data: {"event":"stage.review","stage":"research","passed":false,"discrepancies":2,"iteration":0}
data: {"event":"stage.review","stage":"research","passed":true,"discrepancies":0,"iteration":1}
data: {"event":"stage.done","stage":"research","deliverable":"campaigns/coast-spring/research.md","qa_iterations":1}
data: {"event":"campaign.done","stages":[ … same shape as /run … ]}
```
Event types: `gate.start|gate.passed`, `stage.start`, `stage.save_retry`,
`stage.review`, `stage.done`, `campaign.done`, `error`.

### `GET /campaigns/{slug}/deliverables`
```json
{ "slug":"coast-spring","files":[{"name":"research.md","size_bytes":4210}, …] }
```
Fetch file contents with your own static file serving (writes land under
`campaigns/<slug>/`), or extend the API to stream them.

---

## 4. Library use (same engine, in-process)

**Why**: for tests, batch jobs, or wrapping in a different transport.
```python
from marketing_os import load_settings
from marketing_os.graph.runner import run_campaign

settings = load_settings()                                  # provider from env
result = run_campaign(settings, "coast-coffee", "coast-spring")  # or stage="research"
for s in result.stages:
    print(s.stage, s.deliverable_path, "QA:", s.qa_iterations, "ok:", s.approved)
```
For a compiled graph you can stream or resume yourself, use
`build_campaign_graph(settings, model=…, reviewer=…, web_backend=…, checkpointer=…)`.
The `model` and `reviewer` kwargs make the graph fully injectable for tests.

---

## 5. Notes for production

- **Concurrency**: `run` is synchronous and CPU-light but network-bound on the
  LLM; put it behind a task queue for many campaigns, or use `/stream`.
- **Auth/multitenancy**: not included — front the API with your own auth and map
  tenants to `customer`/`slug`.
- **Cost**: each stage = one specialist loop + up to `MARKETING_OS_MAX_QA`
  reviewer+revision passes. `usage` is returned per stage and per campaign.
- **Idempotence**: re-running a stage overwrites its deliverable; a stage refuses
  to start until its prerequisite deliverable exists (`422`).
- **Resumability**: runs are checkpointed by `thread_id` (the slug). The default
  `MemorySaver` is in-process only — install the `postgres` extra and pass a
  `PostgresSaver` to `build_campaign_graph` for resume across workers/restarts.

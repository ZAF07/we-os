# Usage — Marketing OS (ADK) as an API

**What** this is: an HTTP interface to the ADK coordinator pipeline. **Why** an
API: so a frontend/service can start campaigns, watch progress, and resolve human
approvals without embedding the engine. **How**: every request runs the same
governance the CLI does — Stage-0 gate → coordinator (intake → research →
strategy/creative/media + Evaluator loop → [approval] → execution → performance).

## 1. Run the service

```bash
cd agent-harness
uv sync --extra dev && uv run playwright install chromium
export GOOGLE_API_KEY=...                  # primary provider (Gemini, AI Studio)
export GOOGLE_MODEL=gemini-2.5-flash       # confirm/override the model id
uv run uvicorn marketing_os.api.app:app --reload    # http://127.0.0.1:8000
```

Gemini is native to ADK (no LiteLLM). For Vertex AI instead of an AI Studio key,
set `GOOGLE_GENAI_USE_VERTEXAI=TRUE` + `GOOGLE_CLOUD_PROJECT`/`GOOGLE_CLOUD_LOCATION`.
Swap providers with `MARKETING_OS_PROVIDER=deepseek` (+ `DEEPSEEK_API_KEY`) or
`anthropic`/`openai` — no code change.

## 2. Lifecycle

| Step | What | Endpoint |
|---|---|---|
| 1 | Scaffold `campaigns/<slug>/goal.md` from the template | `POST /campaigns` |
| 2 | Check the Stage-0 gate (DNA + goal complete) | `GET /campaigns/{slug}/gate` |
| 3 | Start the run (background); get a `run_id` | `POST /campaigns/{slug}/run` |
| 4 | Watch progress | `GET /runs/{run_id}` or `GET /runs/{run_id}/stream` |
| 5 | Resolve any human approval | `POST /approvals/{approval_id}` |
| 6 | Fetch deliverables | `GET /campaigns/{slug}/deliverables` |

The Customer DNA (`customers/<name>/dna.md`) is authored once by a human and reused
across campaigns; the API does not create it. If DNA/goal are incomplete the gate
fails and `run` returns `409`.

## 3. Endpoints

```bash
# Health
curl localhost:8000/health

# Scaffold a campaign goal file (then a human fills its <…> placeholders)
curl -X POST localhost:8000/campaigns -H 'content-type: application/json' \
  -d '{"customer":"coast-coffee","slug":"coast-spring"}'
#  → {slug, gate_ok:false, gate_issues:[...]}   # placeholders still unfilled

# Gate
curl "localhost:8000/campaigns/coast-spring/gate?customer=coast-coffee"
#  → {ok:true, issues:[]}

# Start a run (returns immediately)
curl -X POST localhost:8000/campaigns/coast-spring/run -H 'content-type: application/json' \
  -d '{"customer":"coast-coffee"}'
#  → {run_id:"…", status:"running"}

# Poll status (includes result when done + any pending approvals)
curl localhost:8000/runs/<run_id>
#  → {status:"running|paused|done|error", result:{deliverables, violations, steps},
#     pending_approvals:[{approval_id, payload}]}

# Stream progress (SSE: gate.passed, step, agent_event, approval.pending, campaign.done…)
curl -N localhost:8000/runs/<run_id>/stream

# Resolve a human approval (only when approval gate is enabled — see below)
curl -X POST localhost:8000/approvals/<approval_id> -H 'content-type: application/json' \
  -d '{"status":"approved"}'      # or {"status":"rejected","comment":"…"}

# Deliverables written under campaigns/<slug>/
curl localhost:8000/campaigns/coast-spring/deliverables
```

**The structured deliverables** (typed per-stage JSON) are in
`GET /runs/{run_id}.result.deliverables` keyed by stage (`intake, research,
strategy, creative, media, eval, execution, performance`). The markdown files are
under `campaigns/<slug>/`.

## 3a. Resuming runs (checkpoints)

Every run checkpoints its state to `campaigns/<slug>/.run_state.json` after each
stage. Runs **resume by default**: completed stages are skipped and work continues
where it stopped — after a crash, a Ctrl-C, or a transient model error.

- **Transient model errors (e.g. Gemini 503 "high demand") auto-retry in-process**
  with exponential backoff and resume at the failed stage — no action needed.
- **After a hard stop**, just run again — it picks up from the checkpoint:
  - CLI: `uv run marketing-os new-campaign coast-coffee --slug coast-test` (add
    `--fresh` to ignore the checkpoint and start over).
  - API: `POST /campaigns/{slug}/run` again (resume is automatic; pass
    `{"fresh": true}` to start over).
- Inspect progress: `GET /campaigns/{slug}/runstate` → `{checkpoint, completed:[…stages]}`.

The Evaluator refine loop is treated as one unit: it only skips on resume if a
**passing** verdict already exists; a present-but-failed verdict keeps iterating.

## 4. Human approval

Off by default (autonomous runs). To require sign-off, set `approval.enabled: true`
in `marketing_os/agents/agents.yaml` (and/or `human_check: true` on specific
agents). When enabled, the run goes `paused`, surfaces a `pending_approvals` entry
(and an `approval.pending` SSE event with an `approval_id`), and waits until you
`POST /approvals/{approval_id}` — then it resumes in place. (Single-process: the
run lives in the server process; back the run/approval registry with shared storage
for multi-worker deployments.)

## 5. Library use

```python
import asyncio
from marketing_os import load_settings, MarketingDirector

async def main():
    director = MarketingDirector(load_settings())          # provider/keys from env
    result = await director.run_campaign("coast-coffee", "coast-spring")
    print(result.deliverables.keys(), len(result.steps), "steps")

asyncio.run(main())
```

Inject behavior via constructor kwargs: `provider=`, `on_event=` (progress sink),
`approval_handler=` (return the decision dict; may block or be async), `headless=`.

## 6. Notes

- **Cost/latency**: each stage is a worker + formatter LLM call; the strategy
  package may run the Evaluator loop up to `MARKETING_OS_MAX_EVAL` times.
- **Web browsing** is real (Playwright/Chromium) and runs headless server-side.
- **Auth/multitenancy/rate-limiting** are out of scope — front the API with your own.

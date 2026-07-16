Status: ready-for-agent

# A run that fails during graph build writes no trace and resolves to 404 instead of `failed`

## Symptom

When a background run fails **during graph construction** — before its JSONL trace is opened — the run vanishes with no durable record:

- The registry logs `run.registered` immediately followed by `run.deregistered` (~5 ms apart), with **no** `run.start` line.
- **No** trace file is written under `logs/<slug>/<run_id>.jsonl`.
- `GET /runs/{run_id}` returns **HTTP 404 `{"detail":"No run '<run_id>'"}`** rather than a terminal `failed` status.

The failing task's exception is swallowed by `RunRegistry._forget` (which drains `task.exception()` to silence asyncio warnings), so the operator gets no diagnostic anywhere — not in the trace (none written), not over HTTP (404), not surfaced from the API.

The most common trigger is a **misconfigured provider key**: `get_model(settings)` constructs the chat model during graph build and raises `OpenAIError: Missing credentials. Please pass an api_key … or set OPENAI_API_KEY` when no key is present. Any exception raised by `_select_graph` (model construction, spec load, tool wiring) hits this same hole.

Expected: a run that fails after `POST /run` accepted it (202) should end with a terminal `run.summary outcome=error` in its trace, so `GET /runs/{run_id}` resolves to `failed` with a diagnosable reason — consistent with the five-state run lifecycle (see `CONTEXT.md` → **Run**).

Impact: silent failure. An operator who starts a run with a bad/absent key sees `202 running`, then a bare `404` on status poll, with no error text and no log trace to consult.

## Repro

Deterministic. Against a repo with a valid gate for the customer but **no** provider API key set (`DEEPSEEK_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` all unset):

```bash
cd agent-harness
MARKETING_OS_RUN_LOGS=1 uv run uvicorn marketing_os.entrypoints.api.app:app --port 8099 &
# customers/coast-coffee/dna.md + campaigns/coast-coffee/goal.md make the gate pass
RID=$(curl -s -X POST localhost:8099/campaigns/coast-coffee/run \
       -H 'content-type: application/json' \
       -d '{"customer":"coast-coffee","stage":"research"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["run_id"])')
curl -s localhost:8099/runs/$RID        # -> {"detail":"No run '<RID>'"}  (HTTP 404)
ls logs/coast-coffee/$RID.jsonl         # -> No such file or directory
```

Server log shows `run.registered … run_id=<RID>` then `run.deregistered … run_id=<RID>` with no `run.start` in between.

Isolate the underlying throw:

```bash
cd agent-harness
uv run python -c "
from marketing_os.config import load_settings
from marketing_os.graph.graph import build_single_stage_graph
build_single_stage_graph(load_settings(), 'research')"
# -> OpenAIError: Missing credentials …
```

## Suspected location

`agent-harness/src/marketing_os/graph/runner.py` — `arun_campaign` (and `astream_campaign`) build the graph **before** opening the trace:

```python
backend, owns_backend = _resolve_web_backend(settings, web_backend)
graph = _select_graph(settings, stage, web_backend=backend, checkpointer=checkpointer)  # can raise
config = _config(customer, slug, stage)
trace = _open_trace(settings, slug, run_id or new_run_id())   # trace opens only after build succeeds
```

An exception from `_resolve_web_backend`/`_select_graph` escapes before `trace` exists, so the `except Exception` → `_write_error_summary(trace, …)` path never records anything (there is no trace to write to). Compounding it, `RunRegistry._forget` (`graph/registry.py`) consumes the task's exception, so nothing reaches the operator.

Likely fix direction (leave root-cause confirmation to `/diagnosing-bugs`): open the trace (and mint the `run_id`) **before** graph construction so a build-time failure still writes a terminal `error` summary; and/or have the registry surface a failed task's outcome rather than silently draining it. Note the API detaches runs (ADR-0010), so the failure must surface via the trace/status, not the HTTP response.

## Acceptance criteria

- [ ] A run that fails during graph build writes a terminal `run.summary outcome=error` to its trace (with a message identifying the failure, e.g. missing credentials).
- [ ] `GET /runs/{run_id}` for such a run resolves to `failed` (not 404).
- [ ] A test reproduces the build-time failure on the async run path and asserts the trace + `failed` status (red before the fix, green after).
- [ ] Quality gates pass: `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest`.

## Comments

Surfaced during `/verify` of the architecture-deepening refactor (RunLog / error-taxonomy / SpecSource work). Pre-existing defect, unrelated to that diff — the trace-open-after-build ordering predates it. Filed so it isn't lost.

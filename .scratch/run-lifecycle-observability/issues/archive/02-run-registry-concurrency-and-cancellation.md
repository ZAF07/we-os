# Run registry: background-job model with per-slug concurrency guard and cancellation

Status: completed

Blocked by: `03-async-cancellable-pipeline-execution.md` (cancellation cannot abort
in-flight LLM calls without the async execution path), and
`01-terminal-error-event-and-slug-scoped-logs.md` (the terminal-summary wrapper this
issue extends with the `cancelled` outcome, and the `interrupted`-status inference).

## Context

Observed in the same incident as issue 01: a `coast-coffee-test-three` run was still
executing server-side while the operator started and watched a `coast-coffee-test-four`
run, with no way to know the first run existed short of reading interleaved console logs.

Three gaps in the current API (`agent-harness/src/marketing_os/entrypoints/api/app.py`):

- `POST /campaigns/{slug}/run` (`app.py:171-192`) runs the whole pipeline synchronously
  in a FastAPI threadpool thread — uncancellable, so a client disconnect leaves an
  orphaned run with no owner.
- Nothing prevents two concurrent runs, including two runs of the **same** slug, which
  would race on the same deliverable files.
- There is no way to ask "what is running right now?" or to stop a run;
  `GET /campaigns/{slug}/runs` only lists trace files after the fact.

## Decision: background-job model (settled in the 2026-07-04 grilling session)

A **Run** is a single **execution attempt** of a campaign's pipeline, identified by a
unique `run_id` (see the `Run` term in `CONTEXT.md`). The slug names the durable
**campaign**; the run_id names one attempt. **At most one run per slug may be active at
a time.**

- **Start / observe are split.** `POST /run` *starts* a detached background run and
  returns its `run_id` immediately (202). It no longer blocks on the pipeline and no
  longer returns the final result synchronously. Observing a run is a **separate**
  operation — see the sibling issue `04-observe-running-run-via-trace-tailing.md`.
- **Execution.** The run is an `asyncio.Task` running the async graph path (from issue
  03), held in an **in-memory** run registry keyed by slug. In-memory is deliberate for
  now (single-process uvicorn, no persistence layer yet); a restart means "no active
  runs." Durable run state is future work — see
  `.scratch/backfill/issues/07-planned-extensions-approval-postgres-knowledge-writeback.md`.
- **Concurrency guard.** One active run per slug, covering **both** full-pipeline
  (`thread_id = slug`) and single-stage (`thread_id = slug:stage`) runs, since both write
  into `campaigns/<slug>/`. A second run of an already-active slug is rejected with
  **409 Conflict**. Cross-slug runs stay fully concurrent.
- **Cancellation.** `POST /runs/{run_id}/cancel` cancels the run's task **immediately**
  (mid-stage). Because the run executes on the async path (issue 03), cancelling the task
  aborts the in-flight LLM call — the cost driver. An in-flight web fetch is bounded by
  its 20s timeout, not hard-cancelled. Cancel is written as a terminal
  `run.summary outcome=cancelled` event (the **third** outcome alongside `ok`/`error`,
  riding the issue-01 wrapper).
- **Cancel = abandon.** A cancelled run is not resumed; the next run of the slug starts
  clean. This is currently **free**: the API wires no persistent checkpointer — every
  run builds its own ephemeral `MemorySaver` (`graph.py:138`), and the next run re-runs
  from stage 1, overwriting leftover deliverable `.md` files. **Forward dependency:** once
  persistent checkpointing lands (backfill issue 07), abandon must explicitly clear the
  slug's checkpoint thread, else "start clean" silently becomes "resume."
- **Status.** `GET /runs/{run_id}` reports one of: `running` (in the live registry),
  `completed` (`run.summary outcome=ok`), `failed` (`outcome=error`), `cancelled`
  (`outcome=cancelled`), or `interrupted` (trace exists, no terminal summary, not in the
  live registry — a process-restart casualty; inference depends on issue 01). A registry
  listing (`GET /runs` or an extension of the existing per-slug listing) reports active
  runs.

## Acceptance criteria

- [x] `POST /campaigns/{slug}/run` starts a background run and returns its `run_id` immediately (202) instead of blocking on the pipeline. — `app.py` `run()` is now `status_code=202`, checks the gate synchronously (fail-fast 409), then `RunRegistry.start(...)` launches an `asyncio.Task` and returns `{run_id, slug, stage, status: running}` without awaiting the pipeline. Test: `test_run_starts_background_job_and_returns_run_id`.
- [x] A second run for a slug with an already-active run is rejected with 409; runs for different slugs run concurrently. Test covers both. — `RunRegistry.start` claims the slug synchronously and raises `RunConflictError` (mapped to 409 `type=slug_busy`). Tests: `test_api.py::test_second_run_same_slug_conflicts_while_cross_slug_is_concurrent`; registry `test_start_rejects_second_run_for_same_slug`, `test_full_and_single_stage_runs_share_the_slug_guard`, `test_different_slugs_run_concurrently`.
- [x] `POST /runs/{run_id}/cancel` stops the run; the trace ends with `run.summary outcome=cancelled` and the run leaves the live registry. Test asserts the in-flight LLM call was aborted (leans on issue 03's cancellable path). — `RunRegistry.cancel` cancels the task and awaits its unwind; `runner._write_cancelled_summary` writes the third terminal outcome. Test: `test_run_registry.py::test_cancel_aborts_in_flight_call_writes_cancelled_summary_and_deregisters` asserts `model.was_cancelled is True`, the terminal `outcome=cancelled`, and deregistration; API `test_cancel_endpoint_stops_run_and_marks_it_cancelled`.
- [x] `GET /runs/{run_id}` reports the correct status across all five states. Test covers `running`, `completed`, `cancelled`, and the `interrupted` inference (trace with no terminal summary + not live). — `read_run_status` resolves `running` from the registry then maps the terminal trace outcome (`ok→completed`, `error→failed`, `cancelled→cancelled`, no-summary→`interrupted`). Tests: registry `test_status_maps_terminal_outcome[ok|error|cancelled]`, `test_status_is_running_for_a_live_run`, `test_status_is_interrupted_when_trace_has_no_summary`; API `running`/`completed`/`failed`/`cancelled`/`interrupted` all directly asserted.
- [x] The server can report in-flight runs (registry listing). — `GET /runs`; asserted in `test_second_run_same_slug_conflicts_while_cross_slug_is_concurrent`.
- [x] A client disconnect no longer produces an unobservable orphaned run (the run is a first-class background job with queryable status and a cancel handle). — the run is a registry-held `asyncio.Task` detached from the request; queryable via `GET /runs/{run_id}` and stoppable via `POST /runs/{run_id}/cancel`. A pre-restart live run with no terminal summary resolves to `interrupted` (`test_get_run_status_infers_interrupted_from_orphaned_trace`).
- [x] `uv run ruff check .`, `uv run ruff format`, `uv run mypy src`, `uv run pytest` all pass. — ruff + format clean, `mypy src` clean (34 files), `pytest` 129 passed / 1 skipped (manual Postgres smoke).

## Comments

Lets go with the background-job model. this is better suited as when the Customer UI exists, customers should be able to cancel the campaign whenever it is already running.

Note that i also want customers to be able to view in real-time the progress of a running campaign plan if they want to. they dont have to see everything the agent of the system is doing, but more like what steps it is on now, what they found and what are they checking or doing, what the reviewer found and what feedback etc.. (This is now carved out into `04-observe-running-run-via-trace-tailing.md`.)

How the UI/UX will be like is for another session as that belongs to the Frontend side.

## Implementation (2026-07-04)

Built the background-job run model on top of the async cancellable path (issue 03)
and the terminal-summary wrapper (issue 01).

- **`graph/registry.py` (new).** `RunRegistry` holds live runs in an in-memory dict
  keyed by slug (one active run per slug — the guard covers both full-pipeline and
  `slug:stage` runs since both write into `campaigns/<slug>/`). `start()` claims the
  slug synchronously (before scheduling the task) so the guard can't be raced;
  `_forget` (a task done-callback) frees the slug on completion, only evicting the
  entry when it still points at the same run (done-callback race), and retrieves a
  failed task's exception so asyncio doesn't warn it went unconsumed. `cancel()`
  cancels the task and awaits its unwind, so the terminal `cancelled` summary and
  deregistration are guaranteed done before the endpoint returns. `read_run_status`
  resolves the five lifecycle states (live registry → `running`; else the terminal
  trace outcome, or `interrupted` when a trace has no summary).
- **`runner.py`.** `arun_campaign`/`run_campaign` take an optional `run_id` (the API
  mints it up front to register-and-return before the pipeline starts).
  `_write_cancelled_summary` adds the third terminal outcome, written from a new
  `except asyncio.CancelledError` arm that rides the issue-01 wrapper.
- **`errors.py`.** `RunConflictError(slug, active_run_id)` → HTTP 409.
- **`entrypoints/api/app.py`.** `POST /run` → 202 background job (synchronous gate
  fail-fast preserved); new `GET /runs`, `GET /runs/{run_id}`, `POST /runs/{run_id}/cancel`.
  The process registry is a `get_registry()` `lru_cache` singleton (tests reset it
  like `get_settings`).
- **Tests.** `test_run_registry.py` (concurrency guard, cancellation end-to-end
  against the real async runner + `BlockingChatModel`, status mapping); new
  `test_api.py` lifecycle cases. The blocking model fake was consolidated from
  `test_cancellation.py` into `conftest.BlockingChatModel`.

**Code review (both axes).** Standards: no hard violations; addressed the flagged
readability nits (split the opaque `except` tuple in `cancel`; the API now returns
the registry's `RUNNING`/`CANCELLED` status constants instead of raw literals).
Spec: faithful / ship-ready; the one PARTIAL (no direct API-level `failed` assertion)
was closed by asserting the resolved `failed` status in
`test_run_background_job_fails_on_guardrail_failure`.

**Known minor (deferred, not blocking):** the run-outcome vocabulary
(`ok`/`error`/`cancelled`) is emitted as literals by the runner and mapped by the
registry without a single shared definition — a small Shotgun-Surgery seam if a
fourth outcome is ever added. Left as-is since `ok`/`error` predate this change.

**Verified in the running app.** Booted uvicorn against the repo root: `GET /runs`
→ `{"runs":[]}`, `GET /runs/{unknown}` and `POST /runs/{unknown}/cancel` → 404,
`POST /run` with an incomplete gate → 409 `type=gate`, and the OpenAPI schema lists
all three new routes.

## Completion

- Completed: 2026-07-04
- Forward dependency (unchanged): once persistent checkpointing lands (backfill
  issue 07), cancel-as-abandon must explicitly clear the slug's checkpoint thread,
  else "start clean" silently becomes "resume."

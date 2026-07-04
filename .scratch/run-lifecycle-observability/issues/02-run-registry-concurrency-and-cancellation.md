# Run registry: background-job model with per-slug concurrency guard and cancellation

Status: ready-for-agent

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

- [ ] `POST /campaigns/{slug}/run` starts a background run and returns its `run_id` immediately (202) instead of blocking on the pipeline.
- [ ] A second run for a slug with an already-active run is rejected with 409; runs for different slugs run concurrently. Test covers both.
- [ ] `POST /runs/{run_id}/cancel` stops the run; the trace ends with `run.summary outcome=cancelled` and the run leaves the live registry. Test asserts the in-flight LLM call was aborted (leans on issue 03's cancellable path).
- [ ] `GET /runs/{run_id}` reports the correct status across all five states. Test covers `running`, `completed`, `cancelled`, and the `interrupted` inference (trace with no terminal summary + not live).
- [ ] The server can report in-flight runs (registry listing).
- [ ] A client disconnect no longer produces an unobservable orphaned run (the run is a first-class background job with queryable status and a cancel handle).
- [ ] `uv run ruff check .`, `uv run ruff format`, `uv run mypy src`, `uv run pytest` all pass.

## Comments

Lets go with the background-job model. this is better suited as when the Customer UI exists, customers should be able to cancel the campaign whenever it is already running.

Note that i also want customers to be able to view in real-time the progress of a running campaign plan if they want to. they dont have to see everything the agent of the system is doing, but more like what steps it is on now, what they found and what are they checking or doing, what the reviewer found and what feedback etc.. (This is now carved out into `04-observe-running-run-via-trace-tailing.md`.)

How the UI/UX will be like is for another session as that belongs to the Frontend side.

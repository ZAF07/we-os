# Observe a running run in real time (attach, don't start) via trace-tailing

Status: completed

Blocked by: `02-run-registry-concurrency-and-cancellation.md` (a run must be a
detached background job before there is anything to _attach_ to).

## Why this exists

Customers should be able to watch a running campaign plan in real time — not every
internal detail, but "what step is it on now, what did it find, what is it checking,
what did the reviewer flag and what feedback." Today observing and starting are the
**same** action: `GET /campaigns/{slug}/stream` (`app.py:251-274`) calls
`astream_campaign`, which _launches its own graph execution_. In the background-job
model (issue 02) the run is already executing detached from any client, so "watch
progress" must **attach** to the run that is already going — not kick off another.

## Decision (from the 2026-07-04 grilling session)

- **Observing is split from starting** (settled in issue 02). `POST /run` starts the run;
  the stream endpoint only _attaches_.
- **Attach by trace-tailing, for now.** The live feed is served by **tailing the run's
  JSONL trace** (`logs/<slug>/<run_id>.jsonl`) — poll for appended lines, emit each as an
  SSE frame, stop when the terminal `run.summary` event appears. This reuses the durable
  trace we already write on every event, and it makes late-joining and multiple concurrent
  observers trivial (read the file from the top to replay from the start). Cost: sub-second
  polling latency. Chosen for simplicity because there is **no persistent storage layer
  yet** — this is the pragmatic interim, not the "real" design.
- **Deferred to the persistent rebuild:** an in-memory fan-out / pub-sub broker keyed by
  run_id (push events to N subscribers from the moment they attach, no polling). Explicitly
  out of scope here; revisit when the persistence/real-time architecture is built. The
  rationale (fan-out is more "real-time-correct" but adds a broker, backpressure, and
  subscriber-lifecycle surface we don't need yet) is captured so that session inherits it.

## What to build

- Change `GET /campaigns/{slug}/stream` (or a new `GET /runs/{run_id}/stream`) to **attach**
  to an existing run by `run_id` and tail its JSONL trace as SSE, rather than starting a run.
- Support attaching **late**: replay prior events from the top of the trace, then follow
  appended lines to the terminal `run.summary`, then close the stream.
- Attaching to an unknown/finished run should behave sanely (replay a finished run's trace
  and close; 404 for a run_id with no trace).

## Acceptance criteria

- [x] The stream endpoint attaches to an already-running run by `run_id` and does **not** start a new run (test asserts no second run/registry entry is created by observing). — `GET /runs/{run_id}/stream` tails the trace via `tail_trace`; it never calls the runner. Test: `test_stream_attach_does_not_start_a_new_run` asserts `GET /runs` stays empty and no new trace is written after observing.
- [x] A client that attaches after the run has progressed receives the earlier events (replay from the top of the trace) followed by live ones. — `tail_trace` replays every complete line from the top, then polls for appended lines. Unit test `test_tail_trace_replays_then_follows_appended_events` (replay + live follow); API `test_stream_attaches_to_finished_run_replays_trace_and_closes` (late join replays the whole finished trace).
- [x] The stream closes when the terminal `run.summary` event is reached (`ok`, `error`, or `cancelled`). — `tail_trace` returns after yielding `run.summary`. Verified live against a completed trace (`outcome=error`) — stream closed on its own (curl exit 0). An interrupted trace (no summary, not live) also closes rather than hanging: `test_tail_trace_closes_on_interrupted_run_with_no_summary`.
- [x] Multiple concurrent observers of the same run each get the full event sequence. — trace-tailing supports N independent readers; `test_multiple_observers_each_get_the_full_event_sequence` asserts two attaches yield identical full sequences (through `run.summary`).
- [x] `uv run ruff check .`, `uv run ruff format`, `uv run mypy src`, `uv run pytest` all pass. — ruff + format clean, `mypy src` clean (34 files), `pytest` 137 passed / 1 skipped (manual Postgres smoke).

## Implementation (2026-07-04)

Split observing from starting at the HTTP surface, on top of the issue-02 run registry.

- **`adapters/observability.py` — `tail_trace` (new).** The reader counterpart of
  `RunTrace`. An async generator that replays a run's JSONL trace from the top, then
  polls (0.25s default) for appended lines and yields each, closing on the terminal
  `run.summary`. Only newline-terminated lines are yielded (a line mid-write is never
  emitted half-formed). Liveness is sampled _before_ each read, so a run that finishes
  between reads is drained one final time — and since `RunTrace` flushes+closes each
  event before the task deregisters, the terminal summary is always on disk by the time
  `is_live()` reports `False`. An interrupted run (trace, no summary, not live) replays
  and closes rather than polling forever. Waits for a not-yet-created trace file while
  the run is live (handles attaching immediately after `POST /run`).
- **`graph/registry.py` — `resolve_trace_path` (new).** Returns the trace path to tail:
  a live run's path derived from its slug (even before the file exists, so no spurious
  404), else the on-disk trace, else `None` (unknown → 404).
- **`entrypoints/api/app.py`.** Replaced the start-on-stream `GET /campaigns/{slug}/stream`
  (which launched a run via `astream_campaign` — the exact conflation this issue removes)
  with **`GET /runs/{run_id}/stream`**, which attaches by tailing the trace as SSE. 404
  when the run id is neither live nor traced. `astream_campaign` stays in the runner (still
  covered by `test_observability.py`); it simply has no HTTP caller now.
- **Tests.** `test_observability.py`: five `tail_trace` unit tests (replay-and-stop,
  replay-then-follow, interrupted-closes, waits-for-late-file, skips-partial-line).
  `test_api.py`: replaced the old SSE test with attach cases (replay-a-finished-run,
  does-not-start-a-run, 404-unknown, multiple-observers).

**Endpoint change (decision).** The old `GET /campaigns/{slug}/stream` was removed rather
than repurposed: the acceptance criteria and the issue-02 model are `run_id`-centric
(`GET /runs/{run_id}`, `POST /runs/{run_id}/cancel`), and keeping a GET that _starts_ a run
would re-introduce the start/observe conflation. Any client that watched a campaign by
starting-via-stream must now `POST /run` then `GET /runs/{run_id}/stream`.

**Verified in the running app.** Booted uvicorn: OpenAPI lists `/runs/{run_id}/stream` and
no longer lists `/campaigns/{slug}/stream`; `GET /runs/{unknown}/stream` → 404; attaching to
a real completed trace replayed its events and closed on `run.summary` (curl exit 0);
attaching to the interrupted `coast-coffee-test-four` trace (no summary) replayed and closed
without hanging; `GET /runs` stayed `{"runs":[]}` after observing (observing starts nothing).

## Deferred (unchanged, inherited by the persistent rebuild)

- In-memory fan-out / pub-sub broker keyed by `run_id` (push to N subscribers, no polling).
  Out of scope here; revisit when the persistence/real-time architecture is built.

## Completion

- Completed: 2026-07-04
- Commit: `4c76e701560d12e05b3093f9a4fb0a2ee4518404`

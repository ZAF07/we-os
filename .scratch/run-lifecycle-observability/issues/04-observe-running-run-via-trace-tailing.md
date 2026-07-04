# Observe a running run in real time (attach, don't start) via trace-tailing

Status: ready-for-agent

Blocked by: `02-run-registry-concurrency-and-cancellation.md` (a run must be a
detached background job before there is anything to *attach* to).

## Why this exists

Customers should be able to watch a running campaign plan in real time — not every
internal detail, but "what step is it on now, what did it find, what is it checking,
what did the reviewer flag and what feedback." Today observing and starting are the
**same** action: `GET /campaigns/{slug}/stream` (`app.py:251-274`) calls
`astream_campaign`, which *launches its own graph execution*. In the background-job
model (issue 02) the run is already executing detached from any client, so "watch
progress" must **attach** to the run that is already going — not kick off another.

## Decision (from the 2026-07-04 grilling session)

- **Observing is split from starting** (settled in issue 02). `POST /run` starts the run;
  the stream endpoint only *attaches*.
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

- [ ] The stream endpoint attaches to an already-running run by `run_id` and does **not** start a new run (test asserts no second run/registry entry is created by observing).
- [ ] A client that attaches after the run has progressed receives the earlier events (replay from the top of the trace) followed by live ones.
- [ ] The stream closes when the terminal `run.summary` event is reached (`ok`, `error`, or `cancelled`).
- [ ] Multiple concurrent observers of the same run each get the full event sequence.
- [ ] `uv run ruff check .`, `uv run ruff format`, `uv run mypy src`, `uv run pytest` all pass.

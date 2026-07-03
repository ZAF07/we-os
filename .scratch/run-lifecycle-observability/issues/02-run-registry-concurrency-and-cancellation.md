# No run registry: concurrent runs are unmanaged and disconnects can't cancel

Status: needs-triage

## Context

Observed in the same incident as
`.scratch/run-lifecycle-observability/issues/01-terminal-error-event-and-slug-scoped-logs.md`:
a `coast-coffee-test-three` run was still executing server-side while the
operator started and watched a `coast-coffee-test-four` run, with no way to
know the first run existed short of reading interleaved console logs.

## Gaps

- `POST /campaigns/{slug}/run`
  (`agent-harness/src/marketing_os/entrypoints/api/app.py:171-192`) executes
  the whole pipeline synchronously in a FastAPI threadpool thread. Threadpool
  threads cannot be cancelled, so if the client disconnects or times out the
  run keeps going server-side with no owner — a genuine orphaned run.
- Nothing prevents two concurrent runs, including two runs of the *same* slug
  (which would race on the same deliverable files and the same checkpoint
  `thread_id`).
- There is no way to ask the server "what is running right now?" or to stop a
  run; `GET /campaigns/{slug}/runs` only lists trace files after the fact.

## Design decision needed (why needs-triage)

The fix shape is an architectural choice: keep the synchronous endpoint but add
a per-slug run lock (reject a second run with 409), or move runs to a
background-job model (`POST /run` returns a run id immediately; add
`GET /runs/{id}` status and `POST /runs/{id}/cancel`, with a cooperative
cancellation check between stages). The SSE `stream` endpoint partially covers
the second shape already. Pick one before implementation.

## Acceptance criteria (to refine after triage)

- [ ] Two concurrent runs for the same slug cannot race on deliverables/checkpoints.
- [ ] The server can report in-flight runs.
- [ ] A client disconnect no longer produces an unobservable orphaned run (either the run is cancellable or it is a first-class background job with queryable status).

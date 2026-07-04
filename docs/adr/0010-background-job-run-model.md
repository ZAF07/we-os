# 0010 — Background-job run model with a per-slug registry

A run is a **detached background job**, not a request the client blocks on. `POST /campaigns/{slug}/run` launches the pipeline as an `asyncio.Task` held in an **in-memory registry keyed by slug** and returns the `run_id` immediately (202); status and cancellation are separate operations. Building on the async cancellable path from [ADR-0009](0009-async-cancellable-pipeline-execution.md).

## Status

accepted — builds on [ADR-0009](0009-async-cancellable-pipeline-execution.md).

## Context

The synchronous `POST /run` ran the whole pipeline in a FastAPI threadpool thread and returned the final result. Three gaps surfaced in a real incident (a `coast-coffee` run executing server-side, invisible while a second run was watched): the run was **uncancellable** (a client disconnect orphaned it with no owner), nothing prevented **two concurrent runs of the same slug** racing on the same `campaigns/<slug>/` deliverable files, and there was **no way to ask "what is running now?"** or to stop a run.

The product driver is the future Customer UI: a customer must be able to cancel an in-progress campaign (ADR-0009 makes the cancel actually stop LLM billing) and observe live progress. Cancel and observe are therefore first-class, and both need the run to exist independently of the request that started it.

## Decision

- **Start and observe are split.** `POST /run` *starts* a detached run and returns its `run_id` (202); it no longer blocks on the pipeline or returns the result synchronously. Observing is a separate operation (trace-tailing — see issue 04).
- **In-memory registry keyed by slug.** The run is an `asyncio.Task` held in a process-local `RunRegistry`. In-memory is deliberate for now (single-process uvicorn, no persistence layer): a restart means "no active runs," and such a pre-restart run resolves to `interrupted` (a trace with no terminal summary). Durable run state is future work (backfill issue 07).
- **One active run per slug.** The concurrency guard is keyed by **slug**, covering both full-pipeline (`thread_id = slug`) and single-stage (`thread_id = slug:stage`) runs, because both write into `campaigns/<slug>/`. The slug is claimed synchronously at registration so the guard cannot be raced; a second run of an active slug is rejected with **409 Conflict**. Cross-slug runs stay fully concurrent.
- **Cancel = abandon.** `POST /runs/{run_id}/cancel` cancels the task immediately (mid-stage). The terminal `run.summary` is written with a third outcome, `cancelled`, alongside `ok`/`error` (the issue-01 wrapper). A cancelled run is not resumed; the next run of the slug starts clean, overwriting leftover deliverables.
- **Status from registry then trace.** `GET /runs/{run_id}` reports `running` (live in the registry), else maps the terminal trace outcome — `completed` (`ok`), `failed` (`error`), `cancelled` — or `interrupted` (a trace with no terminal summary and not live). `GET /runs` lists in-flight runs.

Considered and rejected:

- **Persistent registry / durable run state now** — no persistence layer exists yet; single-process in-memory is the honest interim. Deferred to backfill issue 07.
- **Guard keyed by `thread_id` (slug + stage)** — would let a full-pipeline run and a single-stage run of the same slug proceed at once and race on the same deliverable files. The guard must be per **slug**.
- **Keep the synchronous blocking endpoint** — cannot support cancel, concurrent-run rejection, or "what is running now?"; leaves client disconnects orphaning runs.

## Consequences

- The gate is checked **synchronously** in `POST /run` before the job is launched, so a misconfigured campaign fails fast (409) instead of spawning a job that would immediately halt.
- **Forward dependency:** cancel-as-abandon is currently free because every run builds its own ephemeral `MemorySaver`. Once persistent checkpointing lands (backfill issue 07), abandon must explicitly **clear the slug's checkpoint thread**, else "start clean" silently becomes "resume."
- The registry is process-local: horizontal scaling (multiple uvicorn workers) would need the durable/shared registry from backfill issue 07 before the per-slug guard holds across processes.

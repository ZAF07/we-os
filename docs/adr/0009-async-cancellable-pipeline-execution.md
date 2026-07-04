# 0009 — Async, cancellable pipeline execution

The graph's node/model/reviewer path runs on the **async** LangGraph path (`graph.astream`, `agent.ainvoke`, `model.ainvoke`) so a run can be launched as a detached `asyncio.Task` and **cancelled mid-flight** — cancelling the task raises `CancelledError` at the awaiting LLM call, which aborts the in-flight provider HTTP request. This revises **ADR-0007**, which deliberately kept the whole chain synchronous.

## Status

accepted — revises [ADR-0007](0007-thread-confined-sync-playwright-backend.md) (ADR-0007's thread-confined sync Playwright backend stays; only its "keep the whole chain sync" stance is overturned).

## Context

The background-job run model (see `.scratch/run-lifecycle-observability/issues/02-run-registry-concurrency-and-cancellation.md`) requires that a customer can cancel an in-progress campaign and that **in-flight LLM calls actually stop**, because a specialist node is a tool-use loop of many LLM calls and an uncancelled run keeps billing after the customer has walked away.

`asyncio.Task.cancel()` only interrupts work `await`-ed on the event loop. The pipeline was fully synchronous — sync nodes calling `agent.invoke` / `model.invoke` — and LangGraph dispatches sync nodes to worker threads. Python cannot kill a thread, so cancellation could stop *launching* new work but never abort the LLM request already running in a thread. The cost the customer wanted to avoid was incurred anyway.

ADR-0007 rejected async because "the whole tool chain is synchronous"; that reasoning was scoped to the Playwright seam and did not weigh run cancellation or cost control. On a platform that must cancel work and stream live progress, asynchronicity is foundational, so that trade-off is re-decided here.

## Decision

Execute a run on the async path. The specialist and review nodes become `async def` and call `ainvoke`, so every LLM call is an awaited coroutine. A run is an `asyncio.Task`; `POST /runs/{id}/cancel` cancels it, and the `CancelledError` aborts the in-flight LLM HTTP request and lands *inside* the specialist's tool-loop, not merely between stages.

The **sync tools are left synchronous.** Under an async node LangGraph runs sync tools on a worker thread, which is fully compatible with ADR-0007 — the thread-confined Playwright backend already accepts calls from any thread. An in-flight web fetch is therefore **not** hard-cancelled; it is bounded by its existing 20s navigation timeout, and no *further* tool calls are launched once cancellation lands. LLM cost — the real concern — is terminated immediately; a single in-flight web fetch is the accepted residue.

Considered and rejected:

- **Between-node cooperative cancellation only** (no async refactor) — cannot abort an in-flight `agent.invoke()` tool-loop, so the customer still pays for many LLM calls after cancelling. Fails the requirement.
- **Async Playwright** (unwind ADR-0007) — invasive and unnecessary; the LLM seam is where cancellation and cost live, not the browser seam.

## Consequences

- ADR-0007's worker-thread confinement is unchanged and still load-bearing; only the "everything stays sync" stance is overturned.
- Terminal-summary handling must cover a **third** outcome, `cancelled`, alongside `ok` and `error` — built on the always-write-a-terminal-summary wrapper from issue 01.
- The CLI's synchronous `run_campaign` may remain sync (no cancellation need there) or delegate to the async path; either is acceptable so long as the API run path is async.

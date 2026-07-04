# Async, cancellable pipeline execution (prerequisite for the background-job run model)

Status: ready-for-agent

## Why this exists

The background-job run model (issue 02) must let a customer cancel an in-progress
campaign **and actually stop the in-flight LLM calls** — a specialist node is a
tool-use loop of many LLM calls, and an uncancelled run keeps billing after the
customer has walked away.

`asyncio.Task.cancel()` only interrupts work `await`-ed on the event loop. Today the
pipeline is fully synchronous: sync nodes call `agent.invoke` / `model.invoke`
(`agent-harness/src/marketing_os/graph/nodes.py:304,318,344`,
`agent-harness/src/marketing_os/adapters/review.py:67`), and LangGraph dispatches sync
nodes to worker threads. Python cannot kill a thread, so cancellation would stop
*launching* new work but never abort the LLM request already running — the cost is
incurred anyway. To abort an in-flight LLM call it must be `await model.ainvoke(...)`
on the event loop.

This decision is recorded in **[ADR-0009](../../../docs/adr/0009-async-cancellable-pipeline-execution.md)**,
which revises **ADR-0007** (the thread-confined sync Playwright backend stays; only its
"keep the whole chain sync" stance is overturned).

## What to build

- Convert the specialist and review nodes to `async def`, calling `agent.ainvoke` /
  `model.ainvoke` so every LLM call is an awaited coroutine. Cancelling the run's task
  then aborts the in-flight LLM HTTP request and lands *inside* the specialist tool-loop,
  not merely between stages.
- Keep the **sync tools synchronous.** Under an async node LangGraph runs sync tools on a
  worker thread — compatible with ADR-0007's thread-confined `PlaywrightWebSearch`, which
  already accepts calls from any thread. An in-flight web fetch is **not** hard-cancelled;
  it is bounded by its existing 20s navigation timeout, and no further tool calls launch
  once cancellation lands. That residue is accepted (see ADR-0009).
- The API run path must execute on the async graph path. The CLI's synchronous
  `run_campaign` may stay sync (no cancellation need) or delegate to the async path.

## Acceptance criteria

- [ ] A run executing on the async path can be cancelled such that an in-flight LLM call is aborted (test: a fake model whose `ainvoke` blocks on an event the test controls; cancel the task; assert the coroutine was cancelled, not left running).
- [ ] Web-enabled stages still work with the thread-confined sync Playwright backend running under async nodes (ADR-0007 behaviour preserved; existing web tests stay green).
- [ ] `uv run ruff check .`, `uv run ruff format`, `uv run mypy src`, `uv run pytest` all pass.

## Notes / decisions (from the 02 grilling session, 2026-07-04)

- This is the async foundation; issue 02 (`Blocked by: 03`) layers the registry,
  concurrency guard, status, and cancel endpoint on top.
- Terminal-summary handling must later cover a **third** outcome, `cancelled`, alongside
  `ok`/`error` — that wrapper comes from issue 01; the `cancelled` outcome is written by 02.

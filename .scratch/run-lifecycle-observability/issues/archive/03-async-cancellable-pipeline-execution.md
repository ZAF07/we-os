# Async, cancellable pipeline execution (prerequisite for the background-job run model)

Status: completed

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
_launching_ new work but never abort the LLM request already running — the cost is
incurred anyway. To abort an in-flight LLM call it must be `await model.ainvoke(...)`
on the event loop.

This decision is recorded in **[ADR-0009](../../../docs/adr/0009-async-cancellable-pipeline-execution.md)**,
which revises **ADR-0007** (the thread-confined sync Playwright backend stays; only its
"keep the whole chain sync" stance is overturned).

## What to build

- Convert the specialist and review nodes to `async def`, calling `agent.ainvoke` /
  `model.ainvoke` so every LLM call is an awaited coroutine. Cancelling the run's task
  then aborts the in-flight LLM HTTP request and lands _inside_ the specialist tool-loop,
  not merely between stages.
- Keep the **sync tools synchronous.** Under an async node LangGraph runs sync tools on a
  worker thread — compatible with ADR-0007's thread-confined `PlaywrightWebSearch`, which
  already accepts calls from any thread. An in-flight web fetch is **not** hard-cancelled;
  it is bounded by its existing 20s navigation timeout, and no further tool calls launch
  once cancellation lands. That residue is accepted (see ADR-0009).
- The API run path must execute on the async graph path. The CLI's synchronous
  `run_campaign` may stay sync (no cancellation need) or delegate to the async path.

## Acceptance criteria

- [x] A run executing on the async path can be cancelled such that an in-flight LLM call is aborted (test: a fake model whose `ainvoke` blocks on an event the test controls; cancel the task; assert the coroutine was cancelled, not left running). — `tests/test_cancellation.py::test_cancel_aborts_in_flight_llm_call`: `_BlockingChatModel._agenerate` sets an event, blocks, and records `was_cancelled` on `CancelledError`; the test cancels the task once the call is in-flight and asserts `was_cancelled is True` and that no deliverable was written.
- [x] Web-enabled stages still work with the thread-confined sync Playwright backend running under async nodes (ADR-0007 behaviour preserved; existing web tests stay green). — all existing `tests/test_websearch.py` stay green, plus a new end-to-end `test_sync_web_tool_runs_under_async_specialist_node` drives a sync web tool through the async specialist node and asserts it runs off the main event-loop thread.
- [x] `uv run ruff check .`, `uv run ruff format`, `uv run mypy src`, `uv run pytest` all pass. — ruff/format clean, `mypy src` clean (33 files), `pytest` 112 passed, 1 skipped (manual Postgres smoke test).

## Notes / decisions (from the 02 grilling session, 2026-07-04)

- This is the async foundation; issue 02 (`Blocked by: 03`) layers the registry,
  concurrency guard, status, and cancel endpoint on top.
- Terminal-summary handling must later cover a **third** outcome, `cancelled`, alongside
  `ok`/`error` — that wrapper comes from issue 01; the `cancelled` outcome is written by 02.

## Comments

**Implementation (2026-07-04).** Converted the specialist and review nodes to
`async def`, awaiting `agent.ainvoke` / `reviewer.areview` so every LLM call is a
coroutine on the event loop; cancelling the run's task now aborts the in-flight
provider request inside the specialist tool-loop.

Key decisions made during implementation:

- **Reviewer port went async.** `Reviewer.review` → `async def areview`, and
  `LLMReviewer` awaits `model.ainvoke`. Fakes (`FakeReviewer`, the crashing stub,
  the structured-output stub) and `test_review.py` were updated to match.
- **The whole run path is async now.** LangGraph's sync `.invoke()`/`.stream()`
  cannot drive async nodes (`TypeError: No synchronous function provided`), so the
  runner's core became `arun_campaign` (drives `astream` + `aget_state`), and the
  sync `run_campaign` is now a thin `asyncio.run(arun_campaign(...))` wrapper for
  the CLI. The API `POST /run` endpoint is `async` and `await`s `arun_campaign`, so
  the run is an `asyncio.Task` on the request loop and is cancellable (issue 02
  layers the cancel endpoint on top). Graph tests moved to `graph.ainvoke`.
- **Tool-error middleware needed an async hook.** `create_agent` dispatches to
  `awrap_tool_call` under async invocation; the `@wrap_tool_call`-decorated
  function only provided the sync hook. Rewrote it as a `RecoverToolErrors(AgentMiddleware)`
  subclass implementing both `wrap_tool_call` and `awrap_tool_call` (shared body
  factored into `_tool_error_message`). Sync tools (the thread-confined Playwright
  backend) are unchanged — LangGraph runs them on a worker thread under the async
  node, preserving ADR-0007.

**Code review (both axes).** Standards: ship-ready, only pre-existing/deliberate
judgement-call smells. Spec: faithful; the one flagged gap — AC2 proven only
architecturally — was closed by adding the end-to-end
`test_sync_web_tool_runs_under_async_specialist_node`.

## Completion

- Completed: 2026-07-04
- Commit: `4441566b53b20b3aa4b05fa12f99097af4de534d`

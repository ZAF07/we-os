# 0007 — Thread-confined sync Playwright web backend

`PlaywrightWebSearch` routes every browser operation through a single dedicated worker thread it owns, created lazily and torn down by `close()`. The executor is not an optimisation and must not be "simplified" away — it is the correctness mechanism that lets the sync Playwright API survive LangGraph's threading model.

## Context

Playwright's sync API is greenlet-bound to the thread that calls `sync_playwright().start()`; touching any of its objects from another thread raises `greenlet.error: cannot switch to a different thread`. LangGraph's `ToolNode` runs each tool batch on a fresh, short-lived `ThreadPoolExecutor` thread, and the runner closes the Web Backend from yet another thread (the FastAPI request thread). The original implementation started the driver on whichever thread made the first tool call, so the second `web_search` of a run — and the runner's `close()` — crashed every web-enabled campaign run (500 on `POST /campaigns/<slug>/run`).

## Decision

Confine all Playwright work to one long-lived worker thread inside the adapter: `search`, `fetch`, and `close` are thin dispatchers that submit the real work to a lazily created single-thread executor (creation lock-guarded, since `ToolNode` executes a batch's tool calls in parallel). Callers may invoke the backend from any thread; the `WebSearchTool` port contract is unchanged.

Considered and rejected:

- **Switch to Playwright's async API** — the whole tool chain (`@tool` functions, specialists, runner) is synchronous, and LangGraph runs sync tools on worker threads anyway; the rewrite would be invasive without removing the affinity problem at the seam.
- **Start and stop the driver per call** — thread-safe but pays ~1s of browser launch on every search/fetch, and a run makes many.
- **Thread-local drivers** — leaks a Chromium per short-lived tool thread with no thread to close them from.

## Consequences

- Web tool calls within a run serialise through the one worker thread: correctness over parallelism, consistent with reusing one browser anyway.
- The public/worker method split (`search` → `_search_on_worker`) exists for thread routing, not layering — collapse it and the bug returns.
- Known open edges (close racing an in-flight call, teardown exception leaving a stale browser handle) are tracked in `.scratch/fix-playwright-enabled-issue/issues/02-harden-web-backend-close-concurrency.md`.

## Evidence

- `agent-harness/src/marketing_os/adapters/tools/websearch_playwright.py` (`_run_on_worker` and the worker-side methods).
- `agent-harness/tests/test_websearch.py` (`test_search_confines_playwright_work_to_one_dedicated_thread`).
- Root cause: `playwright/_impl/_sync_base.py::_sync` (greenlet dispatcher switch); `langgraph/prebuilt/tool_node.py` (`executor.map` per tool batch).

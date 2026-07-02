# Fix Playwright greenlet thread-affinity crash on web-enabled runs

Status: completed

## Parent

`.scratch/backfill/issues/archive/01-implement-playwright-web-search.md` — this is a defect in that implementation.

## What to build

With `MARKETING_OS_WEB=1`, `POST /campaigns/<slug>/run` returned 500 with
`greenlet.error: cannot switch to a different thread (which happens to have exited)`,
twice per run: once inside a `web_search` tool call and again when the runner's
`finally` block called `backend.close()`.

Root cause: `PlaywrightWebSearch` started the sync Playwright driver lazily on
whatever thread made the first tool call. LangGraph's `ToolNode` runs each tool
batch on a fresh, short-lived executor thread, and Playwright's sync API is
greenlet-bound to the thread that started it — so the second tool call (a new
thread, after the first had exited) and the runner-thread `close()` both crashed.

Fix: confine all Playwright work to a single dedicated worker thread owned by
the backend; `search`, `fetch`, and `close` dispatch to it and are safe to call
from any thread. Executor creation is lock-guarded because `ToolNode` executes a
batch's tool calls in parallel.

## Acceptance criteria

- [x] A web-enabled run's second (and later) `web_search`/`web_fetch` tool calls no longer raise `greenlet.error`.
- [x] `backend.close()` from the request thread no longer raises `greenlet.error`.
- [x] Regression test fails before the fix and passes after, using the fake-page seam so the suite still runs without Playwright/Chromium installed.
- [x] `ruff check`, `ruff format`, `mypy src`, and `pytest` all pass.

## Blocked by

None - can start immediately.

## Completion

- Completed: 2026-07-02
- Branch: `fix-playwright-enabled-issue`
- Commit: `8ecc2750c604828e75f109d1bbf6b05af3664805`
- Correct hypothesis: Playwright sync-API thread affinity vs LangGraph's short-lived tool-executor threads.

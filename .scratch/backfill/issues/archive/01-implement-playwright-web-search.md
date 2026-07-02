# Implement the Playwright web search backend

Status: completed

`PlaywrightWebSearch` is a stub — `_new_page()`, `search()`, and `fetch()` all raise `NotImplementedError` on purpose. Until it is implemented, agents that declare `WebSearch`/`WebFetch` (market-research, performance-marketing) fall back to `NoopWebSearch` and reason from Customer DNA only, so no live market data reaches research or performance planning.

## What's needed

- Implement `_new_page()`, `search()`, and `fetch()` using `playwright.sync_api` (keep them synchronous).
- Wire the backend in via the `web_backend=` injection point on the graph builders; gate on `MARKETING_OS_WEB=1`.
- Add tests (currently the web path is untested).

## Evidence

- `agent-harness/src/marketing_os/adapters/tools/websearch_playwright.py:56,71,85` (the three `NotImplementedError`s).
- `agent-harness/TODO.md` §1b; `agent-harness/pyproject.toml` (`playwright>=1.44` extra).

## Completion

- Completed: 2026-07-02
- Commit: `6a93752e091a96fc49d0eaa61c4d7bec7d61d6c9`

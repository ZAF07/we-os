# Web tool navigation errors crash the entire pipeline run

Status: completed

## Symptom

During a `POST /campaigns/coast-coffee-test-four/run`, the market-research
specialist called `web_fetch` on `https://www.perkcoffee.com.sg/` (a domain that
does not resolve). Playwright raised
`playwright._impl._errors.Error: Page.goto: net::ERR_NAME_NOT_RESOLVED`, the
exception propagated out of the tool node, killed the whole graph run, and the
client got a 500 Internal Server Error. Run log:
`logs/coast-coffee-test-four/20260702T144811Z-56860d52.jsonl` (trace stops dead
at `stage.start research`).

## Root cause (confirmed, reproduced)

The failure chain has three links, none of which converts a routine network
failure into a recoverable tool result:

1. `PlaywrightWebSearch._fetch_on_worker`
   (`agent-harness/src/marketing_os/adapters/tools/websearch_playwright.py:250`)
   calls `page.goto()` with no error handling; navigation failures
   (`ERR_NAME_NOT_RESOLVED`, timeouts, TLS errors, HTTP-level aborts) escape as
   raw `playwright._impl._errors.Error`. `_search_on_worker` has the same hole.
2. The `web_fetch` / `web_search` tool adapters
   (`agent-harness/src/marketing_os/adapters/tools/websearch.py:106,118`) pass
   the backend exception straight through.
3. `recover_tool_errors`
   (`agent-harness/src/marketing_os/agents/middleware.py:42`) only catches the
   project's own `ToolError`; LangGraph's default tool node re-raises
   everything else (`tool_node.py:_default_handle_tool_errors`), so the raw
   Playwright error is fatal to the run.

The middleware module docstring already states the intent — bad-path tool calls
should come back to the specialist as recoverable error tool-results. Web
navigation failures are exactly such routine bad paths (LLMs regularly pick
dead or hallucinated URLs from search results), but only filesystem tools raise
`ToolError` today.

## Repro (red-capable, deterministic, ~5s)

```python
from marketing_os.adapters.tools.websearch import web_tools
from marketing_os.adapters.tools.websearch_playwright import PlaywrightWebSearch

backend = PlaywrightWebSearch()
web_fetch = web_tools(backend)["WebFetch"]
web_fetch.invoke({"url": "https://definitely-not-a-real-domain-x9q2.invalid/"})
```

Run under `uv run python` in `agent-harness/`: raises raw
`playwright._impl._errors.Error` (bug present). Green when it raises
`marketing_os.errors.ToolError` or returns an error string. `.invalid` is a
reserved TLD, so the repro never depends on real DNS state.

## What to build

Wrap navigation/browser failures at the backend seam: catch Playwright errors
in `PlaywrightWebSearch.search`/`fetch` (or the worker methods) and raise
`ToolError` with a message that names the URL and the failure, so
`recover_tool_errors` converts it into an error `ToolMessage` and the
specialist retries with a different source instead of the run dying.

Keep the exception scope tight — catch `playwright`'s `Error`/`TimeoutError`,
not bare `Exception`, so genuine harness defects still surface.

## Acceptance criteria

- [x] `web_fetch` on a non-resolving URL surfaces to the specialist as an error tool-result; the graph run continues.
- [x] `web_search` navigation failures behave the same way.
- [x] The repro above goes green.
- [x] Offline tests cover the wrapping (fake backend raising the Playwright error types), no live browser needed.
- [x] `uv run ruff check .`, `uv run ruff format`, `uv run mypy src`, `uv run pytest` all pass.

## Completion

- Completed: 2026-07-04
- Commit: `e50ffe7a2a2e0e85f7bf47e2ad92dfc6f213189b`

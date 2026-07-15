# Tavily web backend adapter (`TavilyWebSearch`) + offline tests

Status: ready-for-agent

## Parent

`.scratch/tavily-websearch/PRD.md` — "Replace primary web search with Tavily".

## What to build

A self-contained `TavilyWebSearch` implementing the existing `WebSearchTool` ABC
(`adapters/tools/websearch.py`) over plain HTTP, in a new module
`adapters/tools/websearch_tavily.py`. It talks to Tavily's `/search` and
`/extract` endpoints via a **dependency-injected `httpx.Client`** (not the
`tavily-python` SDK) so it is trivially fakeable offline. No browser, no
Playwright.

`search(query, max_results)`:
- Over-fetch up to Tavily's max (**20**) in one `/search` request (1 credit flat),
  `include_answer` **off**, `search_depth` from an injected depth value.
- Rank the returned results by Tavily's `score` **descending**, keep the **top
  10** as the internal working set, and return the first `min(max_results, 10)`.
- `score` is used to rank/select **only** — never printed.
- Render kept results to the **existing source-attributed format** (numbered
  title / url / snippet) so the agent sees identical structure regardless of
  backend. Reuse or mirror `_format_results` from `websearch_playwright.py`
  (including the shared `NO_RESULTS_PREFIX` no-results string) rather than
  inventing a new shape.

`fetch(url)`:
- Return readable text via Tavily **`/extract`**, using an injected
  `extract_depth` value (same value drives both depths).

Failure map (decision 5 in the PRD) — this is the heart of the slice:
- **429 / 432 / 433 / 5xx / network error / timeout → recoverable `ToolError`**
  (the fallback chain catches `ToolError` and advances).
- **empty `results[]` → return the shared empty/no-results string** (the chain's
  existing empty-result check advances).
- **401 / 403 invalid key → terminal `ConfigError`** (a non-`ToolError` sibling;
  it propagates out of `_run_chain` unchanged and stops the run loudly — no code
  change to the chain needed).

The API key and the depth value(s) are constructor parameters (DI) — this slice
does **not** read `config.py` or environment; wiring that up is slice 3.

Declare **`httpx`** explicitly in `agent-harness/pyproject.toml` `dependencies`
(it is currently only a transitive dep at 0.28.1) — this adapter is its first
direct consumer.

## Acceptance criteria

- [ ] `TavilyWebSearch.search` over-fetches up to 20, ranks by `score` desc,
      keeps the top 10, renders in the existing title/url/snippet format, and
      returns `min(max_results, 10)` results.
- [ ] `score` never appears in rendered output.
- [ ] `TavilyWebSearch.fetch` returns readable text via Tavily `/extract`.
- [ ] 429 / 432 / 433 / 5xx / network / timeout raise recoverable `ToolError`.
- [ ] Empty `results[]` returns the shared no-results string (same
      `NO_RESULTS_PREFIX` the chain detects).
- [ ] 401 / 403 raise `ConfigError` (not `ToolError`).
- [ ] `httpx.Client` is dependency-injected; no live API calls in the default
      `pytest` run.
- [ ] `include_answer` is off; `search_depth` / `extract_depth` come from the
      injected depth value.
- [ ] `httpx` is declared explicitly in `pyproject.toml`.
- [ ] Offline tests against a faked httpx layer cover every branch above.
- [ ] `uv run ruff check .`, `uv run ruff format`, `uv run mypy src`,
      `uv run pytest` all pass.

## Blocked by

None - can start immediately.

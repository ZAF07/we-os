# Tavily web backend adapter (`TavilyWebSearch`) + offline tests

Status: completed

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

- [x] `TavilyWebSearch.search` over-fetches up to 20, ranks by `score` desc,
      keeps the top 10, renders in the existing title/url/snippet format, and
      returns `min(max_results, 10)` results.
- [x] `score` never appears in rendered output.
- [x] `TavilyWebSearch.fetch` returns readable text via Tavily `/extract`.
- [x] 429 / 432 / 433 / 5xx / network / timeout raise recoverable `ToolError`.
- [x] Empty `results[]` returns the shared no-results string (same
      `NO_RESULTS_PREFIX` the chain detects).
- [x] 401 / 403 raise `ConfigError` (not `ToolError`).
- [x] `httpx.Client` is dependency-injected; no live API calls in the default
      `pytest` run.
- [x] `include_answer` is off; `search_depth` / `extract_depth` come from the
      injected depth value.
- [x] `httpx` is declared explicitly in `pyproject.toml`.
- [x] Offline tests against a faked httpx layer cover every branch above.
- [x] `uv run ruff check .`, `uv run ruff format`, `uv run mypy src`,
      `uv run pytest` all pass.

## Blocked by

None - can start immediately.

## Completion

- Completed: 2026-07-15
- Commit: `280d9b141b4e1df9b7e96036cc352e12ac4d7638`

Evidence: `adapters/tools/websearch_tavily.py` (`TavilyWebSearch` over an injected
`httpx.Client`); shared render helpers moved into `websearch.py` so Tavily does
not import the Playwright module (decoupling per PRD decisions 1–2). 20 offline
tests in `tests/test_websearch_tavily.py` cover over-fetch=20 → rank-by-score →
top-10 → `min(max_results,10)`, score-never-printed, `/extract` fetch, and the
full failure map (429/432/433/5xx/network/timeout → `ToolError`; empty →
no-results string; 401/403 → `ConfigError`). `httpx>=0.28` declared in
`pyproject.toml`. All gates pass.

# PRD: Replace primary web search with Tavily

Status: completed
Category: enhancement
Date: 2026-07-15

## Summary

Add a **Tavily** web backend (`/search` + `/extract`, plain HTTP) and make it the
**primary** search/fetch source for `market-research` and `performance-marketing`,
with the existing Playwright backends (Google → DuckDuckGo) demoted to
**fallback**. Tavily is purpose-built for agent retrieval, returns clean JSON,
and needs no browser — replacing brittle Google/DDG scraping while keeping the
scrapers as a safety net during validation.

The work slots into the existing `WebSearchTool` ABC seam and the
`FallbackWebSearch` chain; it does **not** re-architect either. It is structured
so that removing Playwright entirely later is a config-and-delete change, not a
rewrite.

## Motivation

- Current search scrapes `google.com/search` via headless Chromium
  (`GoogleWebSearch`), which hits consent walls / CAPTCHA (`_GOOGLE_BLOCK_MARKERS`)
  and depends on volatile result markup. DuckDuckGo scraping is the fallback.
- Playwright has been a recurring source of fragility (greenlet/thread-affinity
  bugs, close-concurrency hardening — see `.scratch/fix-playwright-enabled-issue/`).
- Tavily is a stable JSON API designed for LLM agents; the user already has an
  account + API key.

## Design decisions (grilled 2026-07-15)

These are the binding decisions from the grilling session. The "why" is retained
so a future refactor can revisit them deliberately. A companion ADR captures
decisions 1, 2, 4, 5.

| #   | Decision                                                                                                                                                                                                                                                                                                                                                                                                                        | Rationale                                                                                                                                                                                                                                                                                                               |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Tavily = **primary** backend; Playwright (Google → DuckDuckGo) stays as **fallback**. Structured so deleting Playwright later is a config-only change.                                                                                                                                                                                                                                                                          | Honors the existing fallback-chain design (issue #02); lowest-risk; collapse-to-sole-backend is a later deliberate step.                                                                                                                                                                                                |
| 2   | Tavily `fetch()` uses Tavily **`/extract`** — self-contained, no browser.                                                                                                                                                                                                                                                                                                                                                       | Decouples from Playwright so browser removal stays trivial. **Caveat: `/extract` bills credits separately from `/search`, same as search does. If the plan's credit budget is tight, that's the tradeoff vs. free Playwright fetching — but given the fallback chain, Tavily-first / Playwright-fallback covers both.** |
| 3   | Add `WebBackend.TAVILY = "tavily"`; new default order `tavily,google,duckduckgo`; key via **`MARKETING_OS_TAVILY_API_KEY`** in the environment. Missing key → **skip-and-warn** (omit Tavily from the chain, log a warning, fall through to Playwright).                                                                                                                                                                        | Keeps fresh checkouts runnable without a Tavily account, consistent with the existing degrade-to-Noop behavior.                                                                                                                                                                                                         |
| 4   | HTTP via **raw `httpx`** (already a transitive dep, 0.28.1; declare it explicitly in `pyproject.toml`), **not** the `tavily-python` SDK.                                                                                                                                                                                                                                                                                        | Trivially fakeable in offline tests; explicit error→exception mapping; smaller/known dependency surface; the call is just two POSTs.                                                                                                                                                                                    |
| 5   | Failure map: **429 / 432 / 433 / 5xx / network / timeout → recoverable `ToolError`** (chain falls through); **empty `results[]` → return empty result** (chain's existing empty-result check advances); **401 / 403 invalid key → terminal `ConfigError`** (propagates out, run stops loudly).                                                                                                                                  | Quota/transient issues degrade gracefully to scraping; a present-but-rejected key must not silently burn a whole campaign on the fallback engine. `FallbackWebSearch._run_chain` catches only `ToolError`, so raising `ConfigError` (a non-`ToolError` sibling) makes "terminal" work with **no change to the chain**.  |
| 6   | Over-fetch up to Tavily's max (20) in one request (1 credit flat), rank results by `score` descending, keep the **top 10** as the internal working set, return `min(max_results, 10)`. `score` is used to rank/select **only** — never printed. **`include_answer` off**. Render kept results to the **existing source-attributed format** (title / url / snippet) so the agent sees identical structure regardless of backend. | Same 1-credit cost yields a higher-signal subset; Tavily stays a pure retrieval layer so the agents do synthesis (evidence-based, per operating principles).                                                                                                                                                            |
| 7   | `search_depth` / `extract_depth` = **`basic`** for now, exposed as **`MARKETING_OS_TAVILY_SEARCH_DEPTH`** (default `basic`, accepts `basic` \| `advanced`) driving both.                                                                                                                                                                                                                                                        | Validate cheaply first (1 credit/search); promoting to `advanced` (2 credits, richer extraction) is a one-line config change, no code edit.                                                                                                                                                                             |
| 8   | Testing: unit-test the adapter against a **faked `httpx` layer** (DI'd `httpx.Client`); test fallback wiring (recoverable → advance, terminal `ConfigError` → re-raise/stop, missing key → omitted + warned); **no live API calls in the default `pytest` run**; optional env-gated smoke test kept separate.                                                                                                                   | Matches issue #02's offline-test precedent; deterministic suite; DI-over-globals per coding standards.                                                                                                                                                                                                                  |

## Non-goals

- **Not** removing Playwright in this feature — only demoting it to fallback.
  Deleting it is a deliberate follow-up once Tavily is validated (decision 1).
- **Not** building a Tavily SDK wrapper (decision 4).
- **Not** enabling Tavily's `include_answer` / LLM synthesis (decision 6).
- **Not** changing the `WebSearchTool` ABC, the `web_tools` adapters, or the
  agent prompts — the rendered output format is preserved (decision 6).

## Decision 9: `.env` auto-loading (resolved)

The harness reads `os.environ` directly; **there is no `.env` auto-loader** today
(`python-dotenv` is not installed; neither `entrypoints/cli.py` nor
`entrypoints/api/app.py` loads a `.env`), so a `.env` file is not picked up
automatically.

**Resolved: add `python-dotenv`** and load `.env` at both entrypoints so `.env`
"just works". This feature introduces a secret (`MARKETING_OS_TAVILY_API_KEY`)
that belongs in `.env`, so making `.env` load automatically is folded into this
work rather than left to manual `source`.

Implementation notes:

- Add `python-dotenv` as a declared dependency in `pyproject.toml`.
- Call `load_dotenv()` **once, early** at each process entrypoint
  (`entrypoints/cli.py` and `entrypoints/api/app.py`), before `load_settings()`
  reads the environment. Do **not** load inside `config.py` (keep the adapter/
  config layer free of import-time side effects; loading is an entrypoint
  concern).
- `load_dotenv()` must **not override** already-set process env vars (its
  default) — real environment/CI values win over a local `.env`.
- Resolve `.env` relative to the repo root / current working dir; a missing
  `.env` is a no-op (no error).

`example.env` (added alongside this PRD, at `agent-harness/example.env`) is the
copy-paste template for every variable.

## Affected code

- `agent-harness/src/marketing_os/config.py` — add `WebBackend.TAVILY`; change
  `_DEFAULT_WEB_BACKENDS`; add `tavily_api_key` + `tavily_search_depth` to
  `Settings`.
- `agent-harness/src/marketing_os/adapters/tools/websearch_tavily.py` (new) —
  `TavilyWebSearch(WebSearchTool)` implementing `search`/`fetch` over `httpx`.
- `agent-harness/src/marketing_os/adapters/tools/websearch_fallback.py` —
  `build_web_backend` learns to construct the Tavily backend and to
  **skip-and-warn** when the key is absent.
- `agent-harness/src/marketing_os/adapters/tools/__init__.py` — export the new
  backend.
- `agent-harness/pyproject.toml` — declare `httpx` and `python-dotenv`
  explicitly.
- `agent-harness/src/marketing_os/entrypoints/cli.py` and
  `entrypoints/api/app.py` — call `load_dotenv()` once, early, before settings
  are read (decision 9).
- Tests under `agent-harness/tests/` — adapter + wiring, offline.

## Acceptance criteria

- [x] `TavilyWebSearch.search` returns the top-10-by-`score` results (from an
      over-fetch of up to 20) rendered in the existing source-attributed format;
      `min(max_results, 10)` respected.
- [x] `TavilyWebSearch.fetch` returns readable text via Tavily `/extract`.
- [x] `MARKETING_OS_WEB_BACKENDS` default is `tavily,google,duckduckgo`;
      `MARKETING_OS_TAVILY_SEARCH_DEPTH` defaults to `basic` and drives depth.
- [x] Missing `MARKETING_OS_TAVILY_API_KEY` → Tavily omitted from the chain +
      warning logged; run proceeds on Playwright.
- [x] 429/432/433/5xx/network/timeout raise recoverable `ToolError` → chain
      falls through to Google/DuckDuckGo.
- [x] Empty Tavily results → chain advances via existing empty-result detection.
- [x] 401/403 invalid key raises `ConfigError` → propagates out, run stops (does
      **not** fall through).
- [x] Credentials read via `config.py`; nothing secret in code or commits.
- [x] Offline tests (faked `httpx`, DI'd client) cover the above; no live calls
      in the default `pytest` run.
- [x] `uv run ruff check .`, `uv run ruff format`, `uv run mypy src`,
      `uv run pytest` all pass.
- [x] `example.env` present and accurate.
- [x] `python-dotenv` declared; `load_dotenv()` runs at both entrypoints before
      settings are read; process env / CI values are not overridden by `.env`; a
      missing `.env` is a no-op. A `.env` set with `MARKETING_OS_TAVILY_API_KEY`
      is picked up without manual `source`.

## Suggested issue slices (for /to-issues)

1. **Tavily adapter + offline tests** — `TavilyWebSearch` over `httpx`
   (search/extract, over-fetch→top-10, render, failure→exception map). Self-contained.
2. **Config + enum wiring** — `WebBackend.TAVILY`, `Settings` fields, default
   order flip, `MARKETING_OS_TAVILY_SEARCH_DEPTH`.
3. **Fallback build + skip-and-warn** — `build_web_backend` constructs Tavily,
   omits+warns on missing key; wiring tests (advance / terminal / omit).
4. **`.env` auto-loading + `example.env`** — add `python-dotenv`, call
   `load_dotenv()` at both entrypoints (decision 9), ship `example.env`.

## Completion

- Completed: 2026-07-15
- Commit: `280d9b141b4e1df9b7e96036cc352e12ac4d7638`

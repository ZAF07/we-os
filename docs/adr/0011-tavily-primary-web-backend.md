# 0011 — Tavily is the primary web backend; Playwright scraping is demoted to fallback

A Tavily JSON-API backend (`TavilyWebSearch`, `/search` + `/extract` over plain
HTTP) becomes the **primary** web search/fetch source, with the existing
Playwright scrapers (Google → DuckDuckGo, [ADR-0008](0008-google-scraping-web-search-with-fallback-chain.md))
kept as **fallback**. Tavily is purpose-built for agent retrieval and needs no
browser, so it replaces brittle scraping as the default path — but the scrapers
stay wired as a safety net, and the whole thing is structured so removing
Playwright later is a config-and-delete change rather than a rewrite.

## Context

[ADR-0008](0008-google-scraping-web-search-with-fallback-chain.md) already
anticipated this: it deferred (did not reject) a "stable JSON SERP provider that
drops into the same seam and slots into the fallback chain." Playwright has been
a recurring source of fragility (thread-affinity/greenlet bugs, close-concurrency
hardening), and Google actively fights headless automation. Tavily is a stable
JSON API designed for LLM agents; the operator already has an account and key.
The change slots into the existing `WebSearchTool` port and `FallbackWebSearch`
chain — neither is re-architected.

## Decision

- **Primary + fallback, not replacement (PRD decision 1).** New default order
  `tavily,google,duckduckgo`. Collapsing to Tavily-only is a later, deliberate
  config-and-delete step once Tavily is validated — deleting Playwright now would
  be premature.
- **Tavily `fetch()` uses Tavily `/extract` (PRD decision 2)** — self-contained,
  no browser — so `TavilyWebSearch` has zero dependency on the Playwright module
  and browser removal stays trivial. To keep that true, the shared render helpers
  (`_format_results` / `_trim_text` / `NO_RESULTS_PREFIX`) were moved from the
  Playwright module into the shared `websearch.py` base, so both backends render
  identically without either importing the other.
- **Raw `httpx`, not the `tavily-python` SDK (PRD decision 4).** The call is two
  POSTs; a DI'd `httpx.Client` is trivially fakeable offline, keeps error→exception
  mapping explicit, and avoids a larger dependency surface.
- **Failure map that makes "terminal" work with no change to the chain (PRD
  decision 5).** 429 / 432 / 433 / 5xx / network / timeout → recoverable
  `ToolError` (the chain falls through to scraping); empty `results[]` → the
  shared "no results" string (the chain's existing empty check advances); 401 /
  403 invalid key → terminal `ConfigError`. Because `FallbackWebSearch._run_chain`
  catches only `ToolError`, a `ConfigError` (a non-`ToolError` sibling) propagates
  out and stops the run loudly — a present-but-rejected key must not silently burn
  a whole campaign on the fallback scrapers.

## Considered and rejected

- **`tavily-python` SDK.** More ergonomic, but a heavier dependency and less
  transparent error handling for a two-endpoint call; rejected per decision 4.
- **Tavily `/extract` vs. reusing Playwright `fetch`.** Playwright fetch is free
  (no credits) but re-couples Tavily to the browser it is meant to escape; the
  credit cost of `/extract` is accepted, and the fallback chain still covers both.
- **Treat a rejected key as recoverable (fall through to scraping).** Rejected:
  it would silently degrade an entire run to the brittle engine the operator was
  trying to leave. A rejected key is a config error, surfaced as one.

## Consequences

- Tavily bills credits per `/search` and per `/extract`. Depth is `basic` by
  default (1 credit), promotable to `advanced` via `MARKETING_OS_TAVILY_SEARCH_DEPTH`
  with no code change.
- The first web-search **secret** enters the system (`MARKETING_OS_TAVILY_API_KEY`,
  read via `config.py`). A missing key is **skipped with a warning** — Tavily is
  omitted from the chain and the run proceeds on the scrapers — so a fresh
  checkout with no Tavily account still runs (consistent with the degrade-to-Noop
  precedent). This secret is why `.env` now auto-loads at the entrypoints.
- ADR-0008's mechanism (scraping behind the fallback chain) is unchanged for the
  fallback tier; only its framing of **Google as the primary engine** is demoted.

## Evidence

- `agent-harness/src/marketing_os/adapters/tools/websearch_tavily.py` (`TavilyWebSearch`, the `_post` failure map).
- `agent-harness/src/marketing_os/adapters/tools/websearch_fallback.py` (`build_web_backend` Tavily construction + skip-and-warn).
- `agent-harness/src/marketing_os/adapters/tools/websearch.py` (shared render helpers).
- `agent-harness/src/marketing_os/config.py` (`WebBackend.TAVILY`, `tavily_api_key`, `tavily_search_depth`, default order).
- `agent-harness/tests/test_websearch_tavily.py`, `tests/test_websearch.py` (adapter + wiring, offline).

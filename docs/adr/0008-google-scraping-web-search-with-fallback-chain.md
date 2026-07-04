# 0008 — Scrape Google for web search, behind a priority-ordered fallback chain

Web search scrapes `google.com/search` with the existing Playwright browser (`GoogleWebSearch`) rather than calling an official search API, and backends are composed into a config-ordered `FallbackWebSearch` chain (default `google,duckduckgo`) instead of merging results. This looks fragile on purpose — it is a deliberate choice for search freedom and agent site-navigation, with the chain absorbing the fragility.

## Context

The web capability previously scraped only DuckDuckGo. Switching the primary engine to Google raised the obvious question of *how* to reach Google, and what to do when a backend fails. Google actively fights headless automation (consent interstitials, `/sorry/` CAPTCHA redirects, shifting result markup), so any scraper is inherently brittle — which is why the mechanism a future reader sees will look like something to "fix" by adopting an official API.

## Decision

- **Scrape `google.com/search` via Playwright** (`GoogleWebSearch`, subclassing `PlaywrightWebSearch` and reusing its browser lifecycle and `fetch`). Google's anti-automation responses and zero-parse markup are raised as recoverable `ToolError`s so they feed the fallback rather than crash the run (building on [ADR-0006](0006-recoverable-tool-errors-and-slug-anchored-seeds.md)).
- **Compose backends as a priority-ordered fallback chain** (`FallbackWebSearch`), selected by `MARKETING_OS_WEB_BACKENDS` (ordered `google` / `duckduckgo` / `noop`). `search` tries each in order and falls through on a recoverable `ToolError` or empty result; a single configured backend behaves exactly as one backend alone. The chain is itself a `WebSearchTool`, so graph wiring is unchanged ([ADR-0001](0001-ports-and-adapters-architecture.md)).

## Considered and rejected

- **Google Custom Search JSON API (Option 1).** The official, stable route — but it is deprecated / deprecating, needs an API key + Programmable Search Engine ID, and caps the free tier at 100 queries/day. Rejected primarily because it is being wound down, and secondarily because it constrains what the agent can search and navigate.
- **Paid SERP provider (SerpAPI / Serper / Brave).** Stable JSON, but a new paid dependency. Deferred, not rejected: it is a future adapter that drops into the same seam and slots into the fallback chain (a separate issue).
- **Result merging / dedupe across backends.** More results, but the model is deliberately *fallback*, not *merge* — the second backend only runs when the first yields nothing usable, keeping the "use one or both based on config" contract simple.

## Consequences

- The Google scraper is expected to break periodically as markup changes; this is designed for, not a defect. DuckDuckGo as the default fallback keeps a run productive when Google blocks it.
- "Empty result" is signalled two ways today — `GoogleWebSearch` raises `ToolError` on zero-parse, other backends return the shared "no results" string that the chain detects by prefix (`NO_RESULTS_PREFIX`). Both feed the fallback; a future backend whose empty copy differs must raise `ToolError` to fall through.
- No credentials enter the codebase for the default (Google/DDG scraping) path; adding a paid SERP backend later will introduce the first web-search secret, read via `config.py`.

## Evidence

- `agent-harness/src/marketing_os/adapters/tools/websearch_playwright.py` (`GoogleWebSearch._extract_results`, block markers, zero-parse `ToolError`).
- `agent-harness/src/marketing_os/adapters/tools/websearch_fallback.py` (`FallbackWebSearch`, `_BACKEND_FACTORIES`, `build_web_backend`).
- `agent-harness/src/marketing_os/config.py` (`web_backends`, `_parse_web_backends`), `graph/runner.py` (`_resolve_web_backend`).
- `agent-harness/tests/test_websearch.py` (Google parsing, consent/CAPTCHA/zero-parse, fallback fall-through, config-driven resolution).

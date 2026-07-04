# Switch web search from DuckDuckGo scraping to Google

Status: needs-info

## Context

Search is currently DuckDuckGo, hardcoded in three places in
`agent-harness/src/marketing_os/adapters/tools/websearch_playwright.py`:

- the URL template default `https://duckduckgo.com/html/?q={query}` (line 118),
- the result parsing selectors `.result`, `a.result__a`, `.result__snippet`
  (`_search_on_worker`, lines 208–217),
- the DDG redirect-link decoder `_decode_result_href` (lines 44–63).

So this is not a one-line URL swap: the parsing layer is engine-specific.

## Options

1. **Google Custom Search JSON API (recommended).** Official, stable JSON, no
   scraping or browser needed for search (Playwright stays for `web_fetch`).
   Implement as a new `WebSearchTool` backend (plain HTTP), keyed off settings.
   Requires a Google API key + Programmable Search Engine ID; free tier is 100
   queries/day, then $5/1000.
2. **Scrape google.com/search with Playwright.** No API key, but headless
   Chromium hits consent walls and CAPTCHA/bot detection quickly, and Google's
   result markup changes often. Fragile; not recommended.
3. **A paid SERP provider (SerpAPI, Serper, Brave Search API).** Stable JSON,
   simpler than CSE setup, but a new paid dependency.

## Blocked on operator input

- Which option? If (1): create the API key and Programmable Search Engine ID
  and provide them via `.env` (read through `config.py`, per repo standards —
  never in code).

## Acceptance criteria (once unblocked)

- [ ] New backend implements `WebSearchTool.search` (and either implements or delegates `fetch`); selected via settings, with `PlaywrightWebSearch` remaining available.
- [ ] Credentials read from `.env` via `config.py`; nothing secret in code or commits.
- [ ] Search failures raise `ToolError` (recoverable), consistent with `.scratch/web-tool-hardening/issues/01-recover-web-tool-navigation-errors.md`.
- [ ] Offline tests with a fake HTTP layer; `ruff`, `mypy`, `pytest` pass.

# Config: `WebBackend.TAVILY` enum member + Tavily `Settings` fields

Status: ready-for-agent

## Parent

`.scratch/tavily-websearch/PRD.md` — "Replace primary web search with Tavily".

## What to build

Extend `config.py` so Tavily is a selectable, configurable backend — **data
only, no behavior change to the default chain in this slice** (the default-order
flip and the factory land in slice 3, so that the default path never names a
backend with no registered factory in the meantime).

- Add `WebBackend.TAVILY = "tavily"` to the `WebBackend` `StrEnum` (with a
  docstring line matching the existing members).
- Add `Settings.tavily_api_key` resolving from **`MARKETING_OS_TAVILY_API_KEY`**
  (default `None` / unset — a fresh checkout with no key is valid).
- Add `Settings.tavily_search_depth` resolving from
  **`MARKETING_OS_TAVILY_SEARCH_DEPTH`**, default **`basic`**, accepting
  `basic | advanced`. This single value drives both Tavily `search_depth` and
  `extract_depth` downstream. Reject unknown values with a clear `ConfigError`
  (mirror the `_parse_web_backends` validation style).
- **Do not** change `_DEFAULT_WEB_BACKENDS` in this slice — it stays
  `(GOOGLE, DUCKDUCKGO)` until slice 3 adds the Tavily factory.

## Acceptance criteria

- [ ] `WebBackend.TAVILY` exists with value `"tavily"` and is parseable by
      `_parse_web_backends` (`MARKETING_OS_WEB_BACKENDS=tavily,google,duckduckgo`
      resolves without error).
- [ ] `Settings.tavily_api_key` reads `MARKETING_OS_TAVILY_API_KEY`, defaulting
      to unset without error.
- [ ] `Settings.tavily_search_depth` reads `MARKETING_OS_TAVILY_SEARCH_DEPTH`,
      defaults to `basic`, accepts `advanced`, and raises `ConfigError` on any
      other value.
- [ ] `_DEFAULT_WEB_BACKENDS` is unchanged; the existing default chain still
      builds green.
- [ ] Credentials are read via `config.py` only; nothing secret in code.
- [ ] Tests cover the enum member, both new fields, defaults, and the
      depth-validation error path.
- [ ] `uv run ruff check .`, `uv run ruff format`, `uv run mypy src`,
      `uv run pytest` all pass.

## Blocked by

None - can start immediately.

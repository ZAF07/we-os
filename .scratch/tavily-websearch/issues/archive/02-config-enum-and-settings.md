# Config: `WebBackend.TAVILY` enum member + Tavily `Settings` fields

Status: completed

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

- [x] `WebBackend.TAVILY` exists with value `"tavily"` and is parseable by
      `_parse_web_backends` (`MARKETING_OS_WEB_BACKENDS=tavily,google,duckduckgo`
      resolves without error).
- [x] `Settings.tavily_api_key` reads `MARKETING_OS_TAVILY_API_KEY`, defaulting
      to unset without error.
- [x] `Settings.tavily_search_depth` reads `MARKETING_OS_TAVILY_SEARCH_DEPTH`,
      defaults to `basic`, accepts `advanced`, and raises `ConfigError` on any
      other value.
- [x] `_DEFAULT_WEB_BACKENDS` is unchanged; the existing default chain still
      builds green.
- [x] Credentials are read via `config.py` only; nothing secret in code.
- [x] Tests cover the enum member, both new fields, defaults, and the
      depth-validation error path.
- [x] `uv run ruff check .`, `uv run ruff format`, `uv run mypy src`,
      `uv run pytest` all pass.

## Blocked by

None - can start immediately.

## Completion

- Completed: 2026-07-15
- Commit: `280d9b141b4e1df9b7e96036cc352e12ac4d7638`

Evidence: `config.py` adds `WebBackend.TAVILY = "tavily"`, `Settings.tavily_api_key`
(`MARKETING_OS_TAVILY_API_KEY`, `None` when unset), and `Settings.tavily_search_depth`
(`MARKETING_OS_TAVILY_SEARCH_DEPTH`, default `basic`, accepts `advanced`, raises
`ConfigError` otherwise via `_parse_search_depth`). Tests in
`tests/test_websearch.py` ("Tavily config" block) cover parsing, defaults, and
the depth-validation error path.

Note on AC "`_DEFAULT_WEB_BACKENDS` is unchanged": this held at the issue-02
boundary — the config-only slice did not flip the default, so nothing broke
mid-sequence. The default-order flip to `tavily,google,duckduckgo` is delivered
by issue 03 as planned; both slices are completed together. All gates pass.

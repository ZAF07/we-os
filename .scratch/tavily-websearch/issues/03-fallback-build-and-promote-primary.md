# Fallback build: construct Tavily, skip-and-warn, promote to primary backend

Status: ready-for-agent

## Parent

`.scratch/tavily-websearch/PRD.md` — "Replace primary web search with Tavily".

## What to build

Wire the `TavilyWebSearch` adapter (slice 1) into the `FallbackWebSearch` chain
via `build_web_backend` (`adapters/tools/websearch_fallback.py`), read its config
from `Settings` (slice 2), and make Tavily the **primary** backend by default —
this is the slice where the whole feature becomes live.

- Teach `build_web_backend` to construct a `TavilyWebSearch` for
  `WebBackend.TAVILY`, passing `tavily_api_key` and `tavily_search_depth` from
  settings. The current `_BACKEND_FACTORIES` map takes zero-arg factories, so
  `build_web_backend` (and/or the map) needs to thread settings through to the
  Tavily backend without disturbing the existing Google/DuckDuckGo/Noop
  construction — keep the change tight and its docstrings updated.
- **Skip-and-warn** when `MARKETING_OS_TAVILY_API_KEY` is absent: omit Tavily
  from the chain, log a `warning`, and fall through so the run proceeds on
  Playwright (Google → DuckDuckGo). Consistent with the existing
  degrade-to-Noop behavior — a fresh checkout with no key still runs.
- **Flip the default order** to `tavily,google,duckduckgo`: change
  `_DEFAULT_WEB_BACKENDS` in `config.py` to `(TAVILY, GOOGLE, DUCKDUCKGO)`. Safe
  now because the factory exists; do it here, not in slice 2.
- Export `TavilyWebSearch` from `adapters/tools/__init__.py`.

No change to `FallbackWebSearch._run_chain` itself is expected: recoverable
`ToolError` already advances, and a terminal `ConfigError` (from an invalid key)
already propagates because the chain only catches `ToolError` (decision 5).

## Acceptance criteria

- [ ] `MARKETING_OS_WEB_BACKENDS` unset → default chain is
      `tavily,google,duckduckgo` and builds successfully when a key is present.
- [ ] Missing `MARKETING_OS_TAVILY_API_KEY` → Tavily omitted from the chain, a
      warning is logged, and the chain is built from the remaining Playwright
      backends (run proceeds).
- [ ] Recoverable `ToolError` from the Tavily backend advances the chain to
      Google/DuckDuckGo (wiring test with a fake Tavily backend).
- [ ] Empty Tavily results advance the chain via the existing empty-result
      detection.
- [ ] Terminal `ConfigError` (invalid-key backend) propagates out of the chain
      and stops the run — it does **not** fall through.
- [ ] `TavilyWebSearch` is exported from `adapters/tools/__init__.py`.
- [ ] Wiring tests cover: advance-on-recoverable, re-raise-on-terminal, and
      omit-and-warn-on-missing-key — all offline.
- [ ] `uv run ruff check .`, `uv run ruff format`, `uv run mypy src`,
      `uv run pytest` all pass.

## Blocked by

- `.scratch/tavily-websearch/issues/01-tavily-adapter.md` (needs `TavilyWebSearch`)
- `.scratch/tavily-websearch/issues/02-config-enum-and-settings.md` (needs
  `WebBackend.TAVILY` + the `Settings` fields)

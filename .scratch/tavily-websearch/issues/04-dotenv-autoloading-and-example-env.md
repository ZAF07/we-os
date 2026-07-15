# `.env` auto-loading at both entrypoints + `example.env`

Status: ready-for-agent

## Parent

`.scratch/tavily-websearch/PRD.md` — "Replace primary web search with Tavily"
(decision 9).

## What to build

Make a local `.env` "just work" so the new `MARKETING_OS_TAVILY_API_KEY` secret
(and every other var) is picked up without a manual `source`. The harness reads
`os.environ` directly today and has **no** `.env` auto-loader.

- Declare **`python-dotenv`** explicitly in `agent-harness/pyproject.toml`
  `dependencies` (this slice is its consumer).
- Call `load_dotenv()` **once, early** at each process entrypoint —
  `entrypoints/cli.py` and `entrypoints/api/app.py` — **before** `load_settings()`
  reads the environment. Do **not** load inside `config.py` (keep the
  config/adapter layer free of import-time side effects; loading is an entrypoint
  concern).
- `load_dotenv()` must **not override** already-set process env vars (its
  default) — real environment / CI values win over a local `.env`.
- Resolve `.env` relative to the repo root / current working dir; a **missing
  `.env` is a no-op** (no error).
- Ship **`example.env`** at `agent-harness/example.env` as the copy-paste
  template for every variable — including `MARKETING_OS_TAVILY_API_KEY`,
  `MARKETING_OS_TAVILY_SEARCH_DEPTH`, and `MARKETING_OS_WEB_BACKENDS`. (A stub
  already exists at that path from the PRD commit; make it complete and accurate.)

## Acceptance criteria

- [ ] `python-dotenv` is declared in `pyproject.toml`.
- [ ] `load_dotenv()` runs once, early, in both `cli.py` and `api/app.py`, before
      settings are read; it is **not** called inside `config.py`.
- [ ] A `.env` containing `MARKETING_OS_TAVILY_API_KEY=...` is picked up by a run
      started from either entrypoint without manual `source`.
- [ ] An env var already set in the process environment is **not** overridden by
      a conflicting `.env` value.
- [ ] A missing `.env` file is a silent no-op (no error, run proceeds).
- [ ] `example.env` is present at `agent-harness/example.env` and lists every
      relevant variable with accurate names/defaults.
- [ ] `uv run ruff check .`, `uv run ruff format`, `uv run mypy src`,
      `uv run pytest` all pass.

## Blocked by

None - can start immediately.

# TODO — Completing the Harness

What ships working today, and what *you* fill in to make it production-complete.

## Status at a glance

| Area | State | You do |
|---|---|---|
| Chat models (DeepSeek/Anthropic/OpenAI) | working via `adapters/models.py` | confirm the DeepSeek model id; add keys |
| Specialist agents (`create_agent`) | working | nothing required |
| Tools — filesystem | working, write-scoped to `campaigns/**` | nothing required |
| Tools — web search | working (Playwright), gated on `MARKETING_OS_WEB=1` | install the extra + `playwright install chromium` |
| Gate · pipeline · nodes · graph · QA reviewer | working | nothing required |
| Guardrail rubrics (`guardrails/*.md`) | starter rubrics | sharpen to your professional bar |
| Persistence | `MemorySaver` (in-process) | wire `PostgresSaver` for production |

The offline suite (`uv run pytest`) is green and drives the whole graph with a
scripted fake model — no key needed. `uv run ruff check .` and `uv run mypy src`
are clean.

## 1. Must-do to run live

### 1a. Confirm the DeepSeek connection
- **What**: the exact model id for your DeepSeek account.
- **Why**: `config.py` defaults to `deepseek-chat`; `create_agent` needs a model
  that supports function calling.
- **How**: set `DEEPSEEK_API_KEY` (and `DEEPSEEK_MODEL` / `DEEPSEEK_BASE_URL` if
  they differ). To swap providers entirely, set `MARKETING_OS_PROVIDER=anthropic`
  (or `openai`) and the matching key — resolved through `init_chat_model`.

### 1b. Enable web search (the Playwright backend)
- **What**: `adapters/tools/websearch_playwright.py` — `PlaywrightWebSearch`
  now implements `_new_page()`, `search()`, and `fetch()` against
  `playwright.sync_api` (DuckDuckGo HTML endpoint, redirect-unwrapped links).
- **Why**: `market-research` and `performance-marketing` declare `WebSearch`/
  `WebFetch`; without a live backend they get `NoopWebSearch` and reason from DNA
  only. The backend is off by default so the offline suite needs no browser.
- **How**: install the extra — `uv add --optional playwright playwright && uv run
  playwright install chromium` — then set `MARKETING_OS_WEB=1`. The runner wires a
  `PlaywrightWebSearch` via the `web_backend=` injection point automatically
  (`_default_web_backend` in `graph/runner.py`); pass an explicit `web_backend=`
  to `run_campaign` / `build_campaign_graph` to override. Playwright is imported
  lazily and the browser launches on first tool call, so the gate stays cheap.

## 2. Extension points

- **Reviewer model** — set `MARKETING_OS_REVIEWER_MODEL` to run the QA judge on a
  cheaper model than the specialists. The reviewer implements the `Reviewer` port
  (`ports.py`); swap `LLMReviewer` for your own by passing `reviewer=` to the graph.
- **Guardrail rubrics** (`guardrails/*.md`) — the QA bar, scored by
  `adapters/review.py`. Concrete, checkable bullets beat vibes. `MARKETING_OS_MAX_QA`
  (default 3) bounds the revise rounds.
- **Approval policy** — the router in `graph/nodes.py` advances a stage iff the
  verdict passes. To require human sign-off or an "accept with noted issues" policy,
  add a node before `advance` or interrupt on the verdict.
- **Persistence** — pass a `PostgresSaver` (install the `postgres` extra) as
  `checkpointer=` for resume across workers/restarts; the default `MemorySaver` is
  in-process only.
- **New provider** — extend `_PROVIDER_DEFAULTS` in `config.py` and, if it is not
  covered by `init_chat_model`, add a branch in `adapters/models.get_model`.

## 3. How the pieces fit

```
gate → research → brand-strategy → campaign-strategy → creative-brief →
       asset-prompts → performance-plan          (each: enter → specialist → review)

  gate            governance/gate.py         DNA + goal complete? else halt to END
  enter           graph/nodes.py             prereq check; seed task (+DNA); reset state
  specialist      agents/specialist.py       create_agent tool-use loop; writes deliverable
  review          graph/nodes.py             save-check → LLM judge vs guardrails → route
  router          graph/nodes.py             revise (loop) | advance (next) | fail (END)
```

The graph is assembled from `PIPELINE` in `graph/graph.py`; `graph/runner.py`
drives it and maps halting state into the `errors.py` exception hierarchy;
`entrypoints/` are the CLI and FastAPI surfaces.

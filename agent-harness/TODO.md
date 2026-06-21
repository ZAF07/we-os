# TODO — Completing the Harness

What ships working today, and what *you* fill in to make it production-complete.
Each item is **what / why / how**.

---

## 0. Status at a glance

| Area | State | You do |
|---|---|---|
| Provider adapters (DeepSeek/Claude/OpenAI) | working behind one interface | confirm DeepSeek model/URL; add keys |
| Agent loop | `DefaultToolUseLoop` works | extend via seams/hooks as needed |
| Tools — filesystem | working, scoped | nothing required |
| Tools — web search | **stub only** | implement Playwright `search`/`fetch` |
| Gate · pipeline · specialists · QA reviewer · orchestrator | working | nothing required |
| Guardrail rubrics (`guardrails/*.md`) | starter rubrics written | sharpen with your professional bar |
| Approval gate | auto-approve-if-QA-passes | plug human/SaaS sign-off if wanted |

The offline test suite (`pytest`) is green and proves the wiring without a key.

---

## 1. Must-do to run live

### 1a. Confirm the DeepSeek connection
- **What**: the exact model id and base URL for DeepSeek v4 pro.
- **Why**: `config.py` ships placeholders (`deepseek-v4-pro`,
  `https://api.deepseek.com/v1`); a wrong value 404s on first call.
- **How**: set env `DEEPSEEK_MODEL`, `DEEPSEEK_BASE_URL`, `DEEPSEEK_API_KEY`.
  If DeepSeek's tool-call wire format ever diverges from OpenAI's, override the
  translation methods in `providers/deepseek_provider.py` (it currently inherits
  `_chat_base.ChatCompletionsProvider` unchanged).

### 1b. Implement web search (the Playwright stub)
- **What**: `marketing_os/tools/websearch_playwright.py` — `_new_page()`,
  `search(query, max_results)`, `fetch(url)` currently raise `NotImplementedError`.
- **Why**: `market-research` and `performance-marketing` declare `WebSearch`/
  `WebFetch`; without a backend they get the honest "search unavailable" stub
  (`NoopWebSearch`) and reason from DNA only.
- **How**:
  1. `pip install -e '.[playwright]' && playwright install chromium`
  2. Fill the three methods using `playwright.sync_api` (the file has step-by-step
     TODOs). Keep them **synchronous** — the loop dispatches tools synchronously.
  3. Wire it in: pass an instance as `web_backend=` to `MarketingDirector`, e.g.
     ```python
     from marketing_os.tools.websearch_playwright import PlaywrightWebSearch
     MarketingDirector(settings, web_backend=PlaywrightWebSearch())
     ```
  The registry only hands web tools to agents that declared them, so no other
  change is needed.

---

## 2. The loop seams (`marketing_os/loop/base.py`)

**What**: `AgentLoop` is the scaffold. `DefaultToolUseLoop` (`loop/default.py`)
is a complete reference implementation. The seams are overridable methods with
sensible defaults — override only what you need; the loop body stays intact.

**Why**: real agents need behavior the bare loop omits — context trimming,
spend caps, custom stop signals, retries, parallel tools. Putting these on seams
means you change behavior without forking the loop.

**How**: subclass `AgentLoop` (or `DefaultToolUseLoop`) and override a seam, then
pass it via `loop_factory=lambda: MyLoop(hooks)` to `MarketingDirector`.

| Seam | Default | Fill in to… |
|---|---|---|
| `prepare_messages(ctx)` | returns full history | inject reminders, trim/compact long context, add a scratchpad |
| `model_turn(ctx)` | one `provider.complete()` + usage accounting | wrap with custom logging/retry/fallback |
| `execute_tool(ctx, call)` | dispatch via registry | approval gates, sandboxing, parallel/async tool runs, mocking |
| `should_continue(ctx, result)` | continue iff `stop_reason=="tool_use"` and steps < max | token-budget caps, max-tool-call limits, custom stop conditions |
| `on_finish(ctx, result)` | notify hooks | persistence, metrics flush, end-of-run summary |

Minimal example — cap total output tokens:
```python
from marketing_os.loop import DefaultToolUseLoop

class BudgetedLoop(DefaultToolUseLoop):
    def should_continue(self, ctx, result):
        if ctx.usage.output_tokens > 50_000:
            return False
        return super().should_continue(ctx, result)
```

---

## 3. The hooks (`marketing_os/loop/hooks.py`)

**What**: `LoopHooks` is the cross-cutting observer surface; `NoopHooks` is the
default (does nothing); `StreamToStdout` is a ready example.

**Why**: streaming, logging, tracing, budget metering, and **human-in-the-loop
tool approval** are concerns that wrap the loop rather than change its logic.

**How**: subclass `NoopHooks`, override the events you care about, pass as
`hooks=` to `MarketingDirector` (forwarded into the loop).

| Hook | Fires | Use for |
|---|---|---|
| `on_text(delta)` | each streamed text chunk | live UI output |
| `before_step(ctx)` | start of each loop step | progress, step metering |
| `on_assistant_message(ctx, result)` | after each model turn | logging, token accounting |
| `before_tool_call(ctx, call)` | before a tool runs | **approval gate**, audit |
| `after_tool_call(ctx, call, result)` | after a tool runs | logging, redaction |
| `on_finish(ctx, result)` | loop end | metrics flush |

Human approval example:
```python
from marketing_os.loop import NoopHooks
class ApproveWrites(NoopHooks):
    def before_tool_call(self, ctx, call):
        if call.name == "write_file":
            wait_for_human_ok(call.arguments["path"])   # block on your channel
```

---

## 4. The guardrails (`guardrails/*.md`) — the QA bar

**What**: human-written rubrics the QA reviewer scores each deliverable against
(`shared.md` + one per stage).

**Why**: this is *your* professional standard as a marketer/creative director.
The agent cross-references its output against these and iterates to fix
discrepancies before a stage advances. The sharper and more concrete the rubric,
the better the output and the fewer wasted iterations.

**How**: edit the markdown — no code change. Use concrete, checkable bullets
("names actual competitors and how they position"), not vibes ("good research").
The reviewer can only enforce what is stated. To change how many fix-up rounds it
gets, set `MARKETING_OS_MAX_QA` (default 3).

---

## 5. The approval gate (`MarketingDirector(approval=…)`)

**What**: `approval: (stage_key, deliverable_path, ReviewVerdict) -> bool` decides
whether a stage may advance. Default: advance iff QA passed; otherwise the stage
is blocked (`GuardrailError`).

**Why**: client work often needs explicit human sign-off, or a "accept with noted
issues" policy, beyond the automated QA pass.

**How**: pass a callback. Example — require human sign-off even on a QA pass:
```python
def approve(stage, path, verdict):
    return verdict.passed and human_signs_off(stage, path)
MarketingDirector(settings, approval=approve)
```

---

## 6. Optional / hardening

- **Add a provider**: write one adapter (subclass `Provider` or
  `ChatCompletionsProvider`) and `register("name", importer)` in
  `providers/__init__.py`. Nothing else changes.
- **Deliverable contents over HTTP**: `GET /deliverables` lists files; add an
  endpoint to return file bodies if your UI needs them.
- **Auth / multitenancy / rate limiting**: front the FastAPI app (out of scope here).
- **Persistence/telemetry**: emit from `on_event` (orchestrator) and `on_finish`
  (loop) into your store.

---

## 7. What each component is, why it exists, how it completes the harness

| Component | What | Why it's needed | How it completes the whole |
|---|---|---|---|
| `config.py` | env-driven settings + repo-path resolver | one switch for provider/model/limits; finds the `.claude/` governance | every component reads paths/limits from here — single control point |
| `types.py` | normalized `Message`/`ToolCall`/`CompletionResult`/`ReviewVerdict`… | a vendor-neutral vocabulary | lets the loop, agents, and orchestrator stay provider-agnostic |
| `providers/` | adapter pattern over DeepSeek/Claude/OpenAI | swap LLM backends without touching logic | turns "an LLM call" into a uniform `complete()` the loop calls |
| `loop/` | the agent loop scaffold + working default | the actual think→act→observe cycle, extensible | drives every specialist turn; the seam you grow into |
| `tools/` | scoped filesystem + pluggable web + registry | give agents safe, real capabilities; enforce write-scope in code | the "act" half of the loop; gates what agents can do |
| `agents/` | load `.claude/agents/*.md` → `Specialist` | reuse the repo's prompts as the source of truth | each pipeline stage is a Specialist = prompt + tools + loop |
| `governance/rules.py` | concatenate `.claude/rules/*.md` | the non-negotiable principles | prepended to every agent's system prompt |
| `governance/gate.py` | Stage 0 DNA + goal validation | no work on incomplete inputs (garbage-in guard) | the blocking entry condition for the whole pipeline |
| `governance/pipeline.py` | ordered stages + deliverable gating | enforce "never skip / never bypass upstream" | the spine the orchestrator walks |
| `governance/review.py` | LLM-as-judge vs `guardrails/*.md` | enforce the professional bar; self-correct | the QA loop that gates each stage's exit |
| `orchestrator.py` | `MarketingDirector` ties it together | runs gate → pipeline → specialist + QA + approval | the entrypoint the CLI/API both call |
| `cli.py` / `api/app.py` | CLI + FastAPI surfaces | human + machine access | how requests enter the system |
| `guardrails/*.md` | human QA rubrics | encode your standards as data | what `review.py` checks against |

---

## 8. Visual flow — request → campaign → loops → tools → guardrails

```
  CLI: marketing-os new-campaign <customer>          API: POST /campaigns/{slug}/run
                       │                                         │
                       └──────────────┬──────────────────────────┘
                                      ▼
                         ┌───────────────────────────┐
                         │  MarketingDirector          │   (orchestrator.py)
                         └───────────────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────┐
                    │ STAGE 0 GATE  (governance/gate.py)    │
                    │  • customers/<name>/dna.md complete?  │
                    │  • campaigns/<slug>/goal.md complete? │
                    └─────────────────────────────────────┘
                          fail → 409 / stop  │ pass
                                              ▼
        ┌────────────────────────── PIPELINE (pipeline.py) ──────────────────────────┐
        │  research → brand-strategy → campaign-strategy → creative-brief →           │
        │  asset-prompts → performance-plan        (deliverable file = gate to next)  │
        └─────────────────────────────────────────────────────────────────────────-─┘
                                              │  for each stage:
                                              ▼
                         ┌───────────────────────────────────────┐
                         │ Specialist  (agents/specialist.py)      │
                         │ system = rules + Customer DNA + agent   │
                         │          body (.claude/agents/*.md)     │
                         └───────────────────────────────────────┘
                                              │ start(task)
                                              ▼
        ┌──────────────────── AGENT LOOP  (loop/default.py) ─────────────────────┐
        │   ┌──────────────┐  tool_use   ┌───────────────────────────┐           │
        │   │ provider     │────────────▶│ execute_tool (registry)    │           │
        │   │ .complete()  │             │  read_file / write_file /  │           │
        │   │  (DeepSeek/  │◀────────────│  glob / grep / web_search  │ ◀ HOOKS:  │
        │   │  Claude/…)   │ tool_result └───────────────────────────┘  before/  │
        │   └──────────────┘                                            after_*   │
        │          │ end_turn (deliverable written under campaigns/<slug>/)       │
        └──────────┼──────────────────────────────────────────────────────────-──┘
                   ▼
        ┌──────────────────── QA GUARDRAIL LOOP  (review.py) ────────────────────┐
        │  reviewer scores deliverable vs guardrails/<stage>.md + shared.md +     │
        │  operating-principles  →  ReviewVerdict{passed, discrepancies[]}        │
        │                                                                         │
        │   passed? ── no, and iters < MAX_QA ──▶ specialist.resume(fixes) ──┐    │
        │     │                                                              │    │
        │     │◀───────────────────── re-review ─────────────────────────---┘    │
        │     yes (or budget exhausted)                                           │
        └─────────────────────────────────────────────────────────────────-─────┘
                   ▼
        ┌─────────────────────────────────────────┐
        │ approval(stage, path, verdict)            │  default: advance iff passed
        │  not approved → GuardrailError (422/stop) │  (override for human sign-off)
        └─────────────────────────────────────────┘
                   │ approved → next stage … until pipeline complete
                   ▼
        deliverables in campaigns/<slug>/*.md   +   StageResult/CampaignResult
        (events streamed throughout via on_event → SSE / CLI prints)
```

**Reading the flow**: a request hits the Director; the **gate** blocks bad inputs;
the **pipeline** walks stages in mandatory order; each stage runs a **specialist**
inside the **agent loop** (think → tool use → observe, with hooks wrapping tool
calls); the deliverable then passes the **QA guardrail loop**, iterating against
your rubrics; an **approval** decision gates advancement. The seams you fill
(§2–§5) and the web tool (§1b) are the points marked HOOKS / execute_tool /
review / approval above.

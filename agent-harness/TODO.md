# TODO — Completing & Extending the ADK Harness

What ships working, and where to extend. Each item is **what / why / how**.

## 0. Status

| Area | State | You do |
|---|---|---|
| ADK runtime, coordinator, 9 stages | working (30 tests green) | — |
| Provider: Gemini native (primary) + DeepSeek/Claude/OpenAI via LiteLLM | working | confirm Gemini model id; set key |
| Tools: filesystem (scoped) | working | — |
| Tools: **real Playwright browser** | working (tested on local pages) | — |
| Two-tier guardrails + callbacks | working | tune `guardrails/*.md`; extend `hard.py` |
| File-backed cross-task memory | working | optional: swap SQLite LIKE for FTS5/vectors |
| Per-agent tool/human-check config | working | edit `agents.yaml` |
| Human approval (CLI + API resume) | working | enable in `agents.yaml` |
| Live end-to-end LLM run | needs a key | run with `DEEPSEEK_API_KEY` |

## 1. Run live
- **What**: confirm the Gemini model id and set the key.
- **Why**: `config.py` ships `gemini-2.5-flash` as a placeholder; a wrong id 4xxs.
- **How**: `export GOOGLE_API_KEY=… GOOGLE_MODEL=gemini-<your-model>`, then
  `uv run marketing-os new-campaign coast-coffee --slug coast-test`. (For Vertex:
  `GOOGLE_GENAI_USE_VERTEXAI=TRUE` + project/location instead of the key.) Wiring is
  verified up to the model boundary; only the key/model is missing.

## 2. Configure agents (`marketing_os/agents/agents.yaml`)
- **What**: per-agent `tools` allowlist, `confirm` (per-tool human confirmation),
  `human_check` (attach the approval tool), and `approval.enabled`.
- **Why**: this is the single, declarative place to control capability + where
  humans gate — no code change.
- **How**: add/remove capability names (vocabulary listed at the top of the file);
  set `confirm: [write_file]` to gate a tool; set `human_check: true` or
  `approval.enabled: true` to require sign-off.

## 3. Tune guardrails
- **Editable rubrics** (`guardrails/*.md`, repo root): the Evaluator's quality bar.
  Edit freely — concrete, checkable bullets work best.
- **Non-editable floor** (`marketing_os/guardrails/hard.py`): the governance floor
  in code. Extend `HARD_GUARDRAILS` (injected into every prompt) and `scan_output`
  (cheap structural checks) — keep scans high-precision to avoid false positives.

## 4. Extend the agent loop (seams)
- **Callbacks** (`guardrails/callbacks.py`): `after_model_callback` captures the
  DecisionEnvelope + scans output; `before_tool_callback` logs calls. Add an
  `after_tool_callback` or `before_model_callback` here for redaction, budgets, or
  blocking — they're wired the same way (return a value to short-circuit).
- **Evaluator loop**: `MARKETING_OS_MAX_EVAL` bounds iterations; `EscalationGate`
  in `builder.py` decides pass/continue from `state['eval']`. To auto-revise a
  different artifact, change what `refine_loop` wraps in `pipeline.py`.
- **New stage**: add a prompt md + a schema in `schemas.STAGE_SCHEMAS` + an entry in
  `agents.yaml`, then insert `build_stage(ctx, "<key>")` into `build_coordinator`.

## 5. Memory backend
- **What**: cross-task recall is SQLite keyword search (`memory/service.py`).
- **Why/How**: for semantic recall, implement the same `BaseMemoryService` interface
  over FTS5 or a vector store and pass it to the `Runner` in `orchestrator.py` —
  callers and tools (`recall`) don't change.

## 6. Known deprecation (ADK 2.3)
- `SequentialAgent` / `LoopAgent` emit a DeprecationWarning ("use Workflow"). They
  still function. When you migrate, the change is localized to `pipeline.py` and
  `agents/builder.py` (stage = worker+formatter); the rest is unaffected.

---

## What each component is, why it exists, how it completes the harness

| Component | What | Why | Completes |
|---|---|---|---|
| `config.py` | env settings + paths + provider resolution | one control point | every module reads it |
| `model.py` | build `LiteLlm` from config | provider-agnostic | the model all agents share |
| `schemas.py` | DecisionEnvelope + per-stage deliverables | typed I/O + the per-step trace | what formatters emit, what callbacks capture |
| `agents/builder.py` | worker(+tools) / formatter(+schema) / evaluator / gate | ADK's tools-vs-schema split | the agents the coordinator runs |
| `agents/agents.yaml` + `registry.py` | per-agent capability + human-check policy | configurable, not hard-coded | enforces tool access |
| `tools/browser.py` | real Playwright session | actual web browsing | the "act on the web" capability |
| `tools/filesystem.py` | scoped read/write | safe file I/O | deliverable persistence |
| `tools/approval.py` | long-running approval tool | human-in-the-loop | the pause/resume gate |
| `guardrails/hard.py` | non-editable floor | governance that ops can't soften | self-check + scan |
| `guardrails/callbacks.py` | ADK callbacks | live enforcement + capture | guardrails actually fire |
| `guardrails/review.py` | editable rubric loader | professional bar as data | the Evaluator's criteria |
| `memory/service.py` | SQLite MemoryService | cross-task recall | future tasks reuse past work |
| `governance/gate.py` | Stage-0 DNA/goal gate | no work on bad inputs | the blocking entry condition |
| `pipeline.py` | coordinator graph | the 9-stage spine | what the Runner runs |
| `orchestrator.py` | gate→run→approve→persist | ties it together | the entrypoint |
| `cli.py` / `api/app.py` | the two surfaces | human + machine access | how requests enter |

## Visual flow — request → campaign → loops → tools → guardrails

```
 CLI new-campaign <customer>            API POST /campaigns/{slug}/run
              │                                      │
              └──────────────────┬───────────────────┘
                                 ▼
                    MarketingDirector (orchestrator.py)
                                 │
                                 ▼
                 STAGE 0 GATE (governance/gate.py)
            DNA complete? goal complete?  ──fail──▶ 409 / stop
                                 │ pass
                                 ▼
        seed session.state: overall_goal, dna, goal, slug   (shared with all agents)
                                 ▼
            ADK Runner  →  marketing_coordinator (SequentialAgent)
                                 │
   ┌─────────────────────────────┼───────────────────────────────────────────┐
   │ each stage = SequentialAgent[ worker , formatter ]                        │
   │                                                                           │
   │  worker (LlmAgent + tools)        formatter (LlmAgent + output_schema)    │
   │   ├ thinks in DecisionEnvelope     └ emits strict per-stage Pydantic JSON │
   │   ├ calls tools: read/write_file, open_page/click_link/tabs (Playwright), │
   │   │              recall/remember/load_memory                              │
   │   └ callbacks: after_model → capture envelope + scan vs HARD floor;       │
   │               before_tool → log (allowlist already enforced by build)     │
   └─────────────────────────────┬───────────────────────────────────────────┘
   intake → research →            ▼
        refine_loop (LoopAgent): strategy → creative → media → Evaluator → gate
              Evaluator scores vs editable rubric + hard floor → EvalReport
              gate: passed? ──no──▶ loop again (≤ MAX_EVAL)   ──yes──▶ escalate, exit
                                 ▼
        [approval_gate]  request_human_approval → run PAUSES
              CLI prompt  /  API POST /approvals/{id}  → resume          (if enabled)
                                 ▼
            execution → performance   (write asset + monitoring deliverables)
                                 ▼
        session persisted to FileBackedMemoryService (future-task recall)
                                 ▼
        result: typed deliverables + step trace + violations
        (progress streamed throughout via on_event → CLI / SSE)
```

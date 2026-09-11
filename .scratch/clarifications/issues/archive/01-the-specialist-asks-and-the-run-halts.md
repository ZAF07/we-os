# 01 — The specialist asks and the run halts

Status: completed
Type: task

## Parent

[PRD: Clarifications](../PRD.md) · [ADR-0028](../../../docs/adr/0028-clarifications-are-brand-dna-the-specialist-asks-for.md)

## What to build

A **Specialist** that lacks a fact only the business knows asks for it instead of inferring it, and the run waits.

Every specialist gains an `ask_tenant` tool taking a list of questions, each with its text and a short reason. The tool's description carries the Questionnaire rule: ask only for facts the owner uniquely knows, never for positioning, channel choice, or anything the pipeline itself owes the business. Calling it records the questions on the run and halts the stage through the same interrupt the Approval Gate uses. The run and the campaign read `awaiting_clarification`; the holding stage reports it as its state the way a stage at a gate reports `awaiting_approval`. Answering is the next issue; here the run halts and the questions are readable.

A new setting bounds how many times one stage may halt to ask within one run, default 2. Past the cap the run halts with an error of type `clarification` listing what is still missing, mirroring how a spent QA budget halts with type `guardrail`. The run never proceeds on a guess. The partial work before a halt is billed like any model call. The trace gains a `stage.awaiting_clarification` event carrying the questions.

The shared Guardrail gains one line: a recommendation that rests on a fact absent from the Brand DNA fails review. The existing test that no questionnaire question asks for a crafted artifact gains a sibling for the ask tool's rule.

The test-only scripted model gains an ask mode: one configured stage asks a fixed question on its first run and writes its deliverable on the second, so the browser suite can walk the halt without a real model.

On Home, the **Action Queue** shows a **Decision** item for each campaign awaiting clarification, linking to a screen that lists the questions and their reasons. The tag palette changes: Decision red, Setup amber, Stale unchanged. The empty-state copy names a pending question as one reason an item appears.

## Acceptance criteria

- [x] Driving the compiled graph with a model that calls `ask_tenant`, the run halts, its status and the campaign's read `awaiting_clarification`, and the questions and reasons are readable from the run.
- [x] A model that asks more times than the cap halts the run with a `clarification` error naming what is still missing; the cap is read from settings.
- [x] The Usage Ledger is charged for the model calls made before the halt.
- [x] The run trace carries a `stage.awaiting_clarification` event with the questions.
- [x] The tool's description states the Questionnaire rule, and a test checks it the way the questionnaire's own rule is checked.
- [x] The shared rubric contains the "fact absent from the DNA" line and the guardrail-docs test covers it.
- [x] With the scripted model in ask mode, a run halts at the configured stage through the API.
- [x] Home shows a red Decision item for the halted campaign; following it shows the questions and reasons. Setup is amber.
- [x] `make check` and `make test-postgres` pass; `make test-e2e` passes; the halt and the Home item are confirmed in the running app.

## Blocked by

None - can start immediately.

## Comments

**2026-09-11 — plan (agent).** Branch `feat/clarifications-01-ask-and-halt`, worked in a scratchpad worktree.

- Domain: `ClarificationQuestion(question, reason)` and `RunHold(stage, kind, questions)` in `schemas.py`; `CampaignResult.awaiting_clarification_stage`. A hold is what a halted run waits on a person for, `approval` or `clarification`, read from the pending interrupt's payload (both payloads now carry `kind`).
- Tool: `adapters/tools/clarify.py` builds `ask_tenant`; its docstring is the Questionnaire rule. Calling it raises `ClarificationRequested` (a signal, not a `MarketingOSError`), which ends the specialist's loop at once. `build_tools` grants it to every specialist; agent frontmatter is unchanged.
- Graph: the specialist node turns the signal into `route: clarify`; a new `<stage>__clarify` node checks the cap (`Settings.max_clarifications`, `MARKETING_OS_MAX_CLARIFICATIONS`, default 2), emits `stage.awaiting_clarification`, and `interrupt()`s exactly as the Approval Gate does. Past the cap it halts with `error.type = "clarification"` → `ClarificationLimitError`. Resume routes back to the stage's entry node; re-reading the DNA is issue 02.
- Lifecycle: `awaiting_clarification` joins the live run statuses (claim index in Postgres widened), the campaign statuses and stage states in `campaign/progress.py` (which now takes a `RunHold` rather than a stage string), the trace outcomes, and the registry's held statuses. `GET /runs/{run_id}/clarifications` reads the pending questions; 409 when the run is not holding for one.
- Scripted model: `MARKETING_OS_SCRIPTED_ASK_STAGE=<stage>` makes that stage ask a fixed question unless the seeded DNA already carries a `## Clarifications` section. The e2e engine sets it to `performance-plan`, two gates deep, so existing specs are untouched.
- Web: Decision item (red) for `awaiting_clarification` linking to `/campaigns/{slug}/clarifications`, a read-only page listing questions and reasons; the Workspace rail says the stage has a question and links there; the run rail narrates the new event.

**2026-09-11 — done (agent).** Gates on the final tree: `make check` 683 passed; `make test-postgres` 796 passed; `make test-e2e` 74 passed, including the new `clarifications.spec.ts`, which walks two approvals on the scripted stack, sees the Workspace say the plan has a question, finds the red Decision item on Home, and follows it to the questions and reasons. Code review (standards + spec) findings were resolved in the second commit: the limit error carries typed questions, the cap halts with the same `stage.failed` event a spent QA budget emits, re-opening releases a run holding for an answer, the ledger test proves real tokens were charged, and the Postgres suite reads the questions back after a restart. The Home stat tiles became named groups to fix a pre-existing spec race the longer run exposed. Not built here, by design: answering and resuming (issue 02), the DNA `## Clarifications` section (issue 02).

## Completion

- Completed: 2026-09-11
- Commits: `8d64b68` (the slice), `58c562c` (review fixes), `76e3f05` (stat tiles, glossary), on branch `feat/clarifications-01-ask-and-halt`; status commit `77397f6`; merged into `main` as `a7ac06b`.
- Evidence per criterion:
  - Graph halts, run and campaign read `awaiting_clarification`, questions readable — `tests/test_clarifications.py` (`test_the_run_halts_and_reports_the_questions_it_is_holding_for`, `test_the_campaign_and_its_stage_read_awaiting_clarification`, `test_the_questions_and_reasons_are_readable_from_the_run`).
  - Cap from settings, `clarification` error naming what is missing — `test_asking_past_the_cap_halts_with_a_clarification_error`, `test_the_cap_is_read_from_settings`, `test_the_default_cap_is_two`; `config.py` `max_clarifications`.
  - Ledger charged before the halt — `test_the_ledger_is_charged_for_the_work_before_the_halt` (units > 0).
  - Trace carries `stage.awaiting_clarification` with the questions — `test_the_trace_carries_the_questions`.
  - Tool description states the Questionnaire rule; sibling test — `adapters/tools/clarify.py`; `tests/test_questionnaire.py::test_the_ask_tool_states_the_questionnaire_rule`.
  - Shared rubric line and docs test — `guardrails/shared.md` "Asks, never assumes"; `tests/test_guardrail_docs.py::test_shared_rubric_fails_a_recommendation_resting_on_a_fact_absent_from_the_dna`.
  - Scripted ask mode halts through the API — `tests/test_scripted_model.py` ask-mode tests; `web/tests/clarifications.spec.ts` on the compose stack with `MARKETING_OS_SCRIPTED_ASK_STAGE=performance-plan`.
  - Home shows a red Decision item leading to the questions; Setup amber — `web/src/app/(app)/home/page.tsx` `TAG_CLASSES`; `clarifications.spec.ts` asserts `text-red-700`; `onboarding.spec.ts` asserts `text-amber-800`.
  - `make check`, `make test-postgres`, `make test-e2e` pass; halt and Home item confirmed in the running app by the e2e spec above.

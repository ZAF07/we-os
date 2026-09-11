# 02 — The owner answers and the campaign continues

Status: completed
Type: task

## Parent

[PRD: Clarifications](../PRD.md) · [ADR-0028](../../../docs/adr/0028-clarifications-are-brand-dna-the-specialist-asks-for.md)

## What to build

The business owner answers a halted run's questions in the app, the answers become part of their Brand DNA, and the campaign continues on its own.

The screen reached from the Home Decision item shows every pending question with its reason and an answer field, and submits them together. A new endpoint on the run accepts the answers for its pending questions, saves each as a **Clarification**, and resumes the run through the same mechanism approve uses. Answering a run that is not awaiting clarification is refused. The trace gains a `stage.clarified` event.

A Clarification is stored as a tenant-scoped question with an answer, alongside questionnaire answers, carrying the question text, the reason, and the stage and campaign that asked. The Brand DNA markdown renders all of a tenant's Clarifications under a **Clarifications** section after the questionnaire sections, and the DNA read endpoint reports the section. Clarifications are never Required: the DNA Gate and the completeness report ignore them, and questionnaire versioning does not apply.

On resume the stage re-enters from its entry node with a fresh conversation seeded from the re-rendered DNA, the same path revise and reopen use. The specialist's earlier partial work is discarded. A specialist in any later campaign is seeded with the same DNA, so an answered fact is never asked for again.

## Acceptance criteria

- [x] Answering through the API saves the Clarifications, resumes the run, and the stage re-runs with a DNA that carries the Clarifications section; the run reaches its next gate or completes.
- [x] The resumed stage's conversation is seeded with the updated DNA, observable through the model's received messages in the graph test.
- [x] Answering a run that is not awaiting clarification is refused with a clear error.
- [x] The DNA read shows the Clarifications section; the completeness report and the DNA Gate are unchanged by any number of Clarifications.
- [x] A second campaign's specialist is seeded with the Clarifications answered during the first.
- [x] The trace carries `stage.clarified`.
- [x] Resume across a process boundary works on the Postgres checkpointer, as the approval tests cover for approve.
- [x] In the browser suite with the scripted ask mode, answering from Home resumes the run to its next gate.
- [x] `make check` and `make test-postgres` pass; `make test-e2e` passes; the answer flow is confirmed in the running app.

## Blocked by

- [01 — The specialist asks and the run halts](01-the-specialist-asks-and-the-run-halts.md)

## Comments

**2026-09-11 — plan (agent).** Branch `feat/clarifications-02-answer-and-continue`, worked in a scratchpad worktree.

- Domain: `Clarification(id, question, reason, answer, stage, slug, answered_at)` in `schemas.py`; `BrandDnaRecord.clarifications`. A Clarification is a tenant-scoped answer stored beside the questionnaire answers, so one record carries both and the DNA render reads one thing.
- Port: `AnswerStore.add_clarifications(tenant, clarifications)`; in-memory and Postgres adapters (`dna_clarifications` table with the same RLS policy as `dna_answers`). `read()` returns them on the record. Completeness looks only at `answers`, so the gate and the report ignore them by construction; tests pin it.
- Render: `render_brand_dna` appends a `## Clarifications` section after Required/Recommended: a note, then per Clarification a `###` question heading, the answer, and an "Asked by <stage> for campaign <slug>: <reason>" line. Headings keep the field walker from misreading them. The scripted model imports the heading from `render.py` instead of spelling its own.
- Graph: the clarify node takes the document store; once the interrupt returns it re-reads `dna.md`, emits `stage.clarified`, and puts the fresh DNA on state, so the entry node's fresh conversation is seeded from the updated DNA — the same seeding path revise and reopen use. Nothing else in the graph changes.
- API: `POST /runs/{run_id}/clarifications` with `{"answers": [{"question", "answer"}]}`. 404 unknown run; 409 `run_not_awaiting_clarification` when not holding for one; 422 when a pending question is unanswered or an answer names a question that was not asked; 402 when credits are spent (the stage re-runs, which bills). Saves the Clarifications, re-projects `dna.md`, resumes through the same relaunch path approve uses (`_relaunch`, generalised over the hold kind; registry `resume` and `mark_held` accept both held statuses). `GET /brand-dna` gains `clarifications`.
- Web: the clarifications page becomes a form (one textarea per question, "Send answers"), posting through `answerClarificationsAction`, then lands on the Workspace, which follows the run to its next gate. Run rail narrates `stage.clarified`.
- Tests: graph (answer → stage re-runs from a DNA carrying the section, seen in the model's received messages; second campaign seeded with it; trace carries `stage.clarified`), API (all refusals, DNA read, completeness unchanged), Postgres (clarification rows isolated by RLS; resume across a process boundary as the approve test does), seed script purges `dna_clarifications` on reset, e2e spec answers from Home and reaches the next gate.

**2026-09-11 — done (agent).** Gates on the final tree (`9b21ce0`): `make check` 704 passed; `make test-postgres` 821 passed; `make test-e2e` 74 passed, including the extended `clarifications.spec.ts`, which answers the scripted question from Home, lands on the Workspace, watches the plan re-run to its own gate, and sees Home stop leading to the questions. Code review (standards + spec) findings resolved in the second commit: the answers are saved inside the relaunch's synchronous window after a fresh status read and an ownership check (a colleague or a racing second submission is refused with nothing written); blank and unanswered answers are one rule in one place; answers render as blockquotes so an owner answering in the field format can never touch a Required field; Postgres orders a batch by an ordinal, not the shared timestamp; the restart test goes through the Postgres answer store; the test fixture is shared. The performance spec's heading locator became exact, since the suite now leaves a plan behind. Not built here, by design: editing a Clarification and the Brand page tab (issue 03), the review reminder (issues 04–05).

## Completion

- Completed: 2026-09-11
- Commits: `fd4af45` (the slice), `9b21ce0` (review fixes), on branch `feat/clarifications-02-answer-and-continue`; status commit and merge into `main`: see below.
- Evidence per criterion:
  - Answering saves the Clarifications, resumes the run, the stage re-runs with a DNA carrying the section, and reaches its next gate — `tests/test_clarifications.py::test_answering_saves_the_clarifications_and_the_run_continues_to_its_next_gate` (API), `::test_answering_re_runs_the_stage_from_the_updated_dna` (graph).
  - Resumed stage seeded with the updated DNA, observable in the model's received messages — `test_answering_re_runs_the_stage_from_the_updated_dna` asserts the `## Clarifications` section and both answers in the conversation the specialist was handed (`ProgrammableChatModel.received`).
  - Answering a run not awaiting clarification is refused — `test_answering_a_run_that_is_not_asking_is_refused` (409 `run_not_awaiting_clarification`); unknown run 404; unanswered, blank, or unasked question 422; a colleague 404 with nothing saved.
  - DNA read shows the section; completeness and the gate unchanged — `GET /brand-dna` carries `clarifications` and the markdown section (API test above); `test_the_completeness_report_ignores_the_clarifications`; `tests/test_questionnaire.py::test_clarifications_never_count_toward_completeness`; `tests/test_gate.py::test_gate_is_unchanged_by_any_number_of_clarifications` and `::test_an_answer_written_in_the_field_format_cannot_touch_a_required_field`.
  - A second campaign's specialist is seeded with the first's Clarifications — `test_a_later_campaign_is_seeded_with_the_answer_and_never_asks_again`.
  - Trace carries `stage.clarified` — `test_the_trace_carries_the_answer` (graph, ordered after `stage.awaiting_clarification` and before the re-run's `stage.start`), `test_the_stage_re_runs_from_the_dna_the_answers_were_saved_into` (API trace).
  - Resume across a process boundary on Postgres — `tests/test_postgres.py::test_a_run_holding_for_a_question_continues_after_a_restart_once_answered`, through `PostgresAnswerStore.add_clarifications`; RLS pinned by `test_one_business_cannot_read_anothers_clarifications`.
  - Browser suite: answering from Home resumes the run to its next gate — `web/tests/clarifications.spec.ts` on the compose stack ("Approving starts Creative brief." after the answer).
  - `make check`, `make test-postgres`, `make test-e2e` pass on `9b21ce0`; the answer flow is confirmed in the running app by the e2e spec above.

# 02 — The owner answers and the campaign continues

Status: ready-for-agent
Type: task

## Parent

[PRD: Clarifications](../PRD.md) · [ADR-0028](../../../docs/adr/0028-clarifications-are-brand-dna-the-specialist-asks-for.md)

## What to build

The business owner answers a halted run's questions in the app, the answers become part of their Brand DNA, and the campaign continues on its own.

The screen reached from the Home Decision item shows every pending question with its reason and an answer field, and submits them together. A new endpoint on the run accepts the answers for its pending questions, saves each as a **Clarification**, and resumes the run through the same mechanism approve uses. Answering a run that is not awaiting clarification is refused. The trace gains a `stage.clarified` event.

A Clarification is stored as a tenant-scoped question with an answer, alongside questionnaire answers, carrying the question text, the reason, and the stage and campaign that asked. The Brand DNA markdown renders all of a tenant's Clarifications under a **Clarifications** section after the questionnaire sections, and the DNA read endpoint reports the section. Clarifications are never Required: the DNA Gate and the completeness report ignore them, and questionnaire versioning does not apply.

On resume the stage re-enters from its entry node with a fresh conversation seeded from the re-rendered DNA, the same path revise and reopen use. The specialist's earlier partial work is discarded. A specialist in any later campaign is seeded with the same DNA, so an answered fact is never asked for again.

## Acceptance criteria

- [ ] Answering through the API saves the Clarifications, resumes the run, and the stage re-runs with a DNA that carries the Clarifications section; the run reaches its next gate or completes.
- [ ] The resumed stage's conversation is seeded with the updated DNA, observable through the model's received messages in the graph test.
- [ ] Answering a run that is not awaiting clarification is refused with a clear error.
- [ ] The DNA read shows the Clarifications section; the completeness report and the DNA Gate are unchanged by any number of Clarifications.
- [ ] A second campaign's specialist is seeded with the Clarifications answered during the first.
- [ ] The trace carries `stage.clarified`.
- [ ] Resume across a process boundary works on the Postgres checkpointer, as the approval tests cover for approve.
- [ ] In the browser suite with the scripted ask mode, answering from Home resumes the run to its next gate.
- [ ] `make check` and `make test-postgres` pass; `make test-e2e` passes; the answer flow is confirmed in the running app.

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

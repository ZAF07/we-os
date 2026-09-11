# 01 — The specialist asks and the run halts

Status: ready-for-agent
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

- [ ] Driving the compiled graph with a model that calls `ask_tenant`, the run halts, its status and the campaign's read `awaiting_clarification`, and the questions and reasons are readable from the run.
- [ ] A model that asks more times than the cap halts the run with a `clarification` error naming what is still missing; the cap is read from settings.
- [ ] The Usage Ledger is charged for the model calls made before the halt.
- [ ] The run trace carries a `stage.awaiting_clarification` event with the questions.
- [ ] The tool's description states the Questionnaire rule, and a test checks it the way the questionnaire's own rule is checked.
- [ ] The shared rubric contains the "fact absent from the DNA" line and the guardrail-docs test covers it.
- [ ] With the scripted model in ask mode, a run halts at the configured stage through the API.
- [ ] Home shows a red Decision item for the halted campaign; following it shows the questions and reasons. Setup is amber.
- [ ] `make check` and `make test-postgres` pass; `make test-e2e` passes; the halt and the Home item are confirmed in the running app.

## Blocked by

None - can start immediately.

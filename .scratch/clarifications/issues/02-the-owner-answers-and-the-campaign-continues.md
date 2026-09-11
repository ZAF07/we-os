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

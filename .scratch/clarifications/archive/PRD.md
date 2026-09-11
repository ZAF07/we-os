# PRD: Clarifications — the specialist asks the tenant, never guesses

Status: completed
Category: feature
Date: 2026-09-11

Governed by ADRs [0028](../../../docs/adr/0028-clarifications-are-brand-dna-the-specialist-asks-for.md) (this feature), [0018](../../../docs/adr/0018-human-authored-dna-from-a-curated-questionnaire.md) (the exception it makes), [0015](../../../docs/adr/0015-human-approval-gates-and-versioned-deliverables.md) (the halt-and-resume it reuses), [0017](../../../docs/adr/0017-stages-and-lifecycle-are-separate-axes.md), [0025](../../../docs/adr/0025-one-campaign-one-person-and-a-single-worker.md), [0001](../../../docs/adr/0001-ports-and-adapters-architecture.md). Vocabulary per [CONTEXT.md](../../../CONTEXT.md): **Clarification**, **Brand DNA**, **Questionnaire**, **DNA Gate**, **Specialist**, **Stage**, **Action Queue**, **Guardrail**, **Usage Ledger**, **Tenant**.

## Problem Statement

A specialist working a stage sometimes needs a fact about the business that the Brand DNA never captured. Today it has two choices, and both are wrong: it invents the answer, or it writes a deliverable that quietly rests on an assumption. A real run for a current tenant proposed email outreach as a channel without knowing whether the business has an email list. If it has none, the channel plan is useless; the right move is to ask, and if the answer is no, to recommend building a list and explain how.

The business owner has no way to know a question was ever open, no way to answer it, and no way to see or correct the facts a specialist relied on later. And nothing ever asks the owner to look at their Brand DNA again, so the facts every campaign is grounded in drift out of date.

## Solution

When a specialist finds a fact missing from the Brand DNA, it asks the business rather than inferring. The run halts, the campaign reads `awaiting_clarification`, and the owner sees the questions on Home under the Action Queue as a **Decision** item. They answer in the app; the answers are saved into their Brand DNA under a new **Clarifications** section; the stage re-runs from the updated DNA and the campaign continues.

Every later campaign reads the same DNA, so the same fact is asked for once. The Brand page gains a **Clarifications** tab where the owner can read and edit every answer they ever gave a specialist. Editing reruns nothing.

The platform periodically asks the owner to review their Brand DNA and their Clarifications: one email through Resend per due tenant, and a **Review** item in the Action Queue. Both derive from a single reviewed-at timestamp. The interval is a setting, one minute in dev and weekly in production.

## User Stories

1. As a business owner, I want a specialist to ask me for a fact it lacks instead of guessing, so that no recommendation rests on something made up about my business.
2. As a business owner, I want the run to pause while it waits for my answer, so that nothing downstream is built on an unanswered question.
3. As a business owner, I want to see every open question for a campaign in the Action Queue on Home, tagged Decision in red, so that I know a run is blocked on me.
4. As a business owner, I want to answer all of a stage's questions on one screen, so that I am not pestered one fact at a time.
5. As a business owner, I want each question to say why the specialist is asking, so that I can give a useful answer.
6. As a business owner, I want the campaign to continue on its own once I have answered, so that I do not have to restart anything.
7. As a business owner, I want my answers saved to my Brand DNA, so that the next campaign does not ask me the same thing.
8. As a business owner, I want a Clarifications tab on the Brand page listing every answer I gave a specialist, so that I can see what the system knows about me beyond the questionnaire.
9. As a business owner, I want to edit any Clarification answer when something changes, so that future campaigns use the current truth.
10. As a business owner, I want editing an answer to leave my existing campaigns alone, so that a retrospective correction never burns credits or overwrites approved work.
11. As a business owner, I want to be reminded periodically to review my Brand DNA and Clarifications, so that stale facts do not quietly ground new campaigns.
12. As a business owner, I want that reminder by email, so that I hear about it without opening the app.
13. As a business owner, I want the same reminder as a Review item in the Action Queue, tagged amber, so that I see it in the app too and can tell it is less urgent than a Decision.
14. As a business owner, I want a Reviewed action on the Brand page, so that I can dismiss the reminder when everything is still correct.
15. As a business owner, I want saving any DNA or Clarification answer to count as a review, so that I am not asked to review what I just edited.
16. As a business owner, I want to receive one reminder per period, not one per tick, so that the platform does not spam me.
17. As a business owner, I want a stage that keeps asking without progress to stop with a clear message, so that a confused specialist cannot spend my credits indefinitely.
18. As a business owner, I want the Clarifications section to never block the DNA Gate, so that a new question from a specialist never locks me out of running campaigns.
19. As a specialist, I want a tool to ask the business a list of questions, so that I can batch everything I am missing into one halt.
20. As a specialist, I want the tool to refuse questions about positioning, channel choice, or other things the pipeline owes the business, so that I only ever ask for facts the owner uniquely knows.
21. As a specialist, I want the Brand DNA I am seeded with to include every Clarification already answered, so that I never ask what has been answered.
22. As a QA reviewer, I want the shared Guardrail to fail any recommendation resting on a fact absent from the DNA, so that asking is cheaper for the specialist than guessing.
23. As a platform admin, I want the review interval, the mailer, and the clarification cap to be settings, so that I can move from a one-minute dev interval to a weekly one without a deploy.
24. As a platform admin, I want a no-op mailer for tests and local development, so that no run ever emails a real address by accident.
25. As a platform admin, I want the reminder loop to run inside the single engine process, so that there is no second process to coordinate with.
26. As a platform admin, I want every clarification event in the run trace, so that I can see when a run asked, what it asked, and when it resumed.
27. As a platform admin, I want the discarded partial run before a halt billed like any model call, so that the Usage Ledger stays honest.

## Implementation Decisions

**The ask tool.** Every specialist gains an `ask_tenant` tool taking a list of questions, each with the question text and a short reason. Its description carries the Questionnaire rule: only facts the owner uniquely knows, never crafted artifacts. Calling it records the questions on the run and halts the stage through the same LangGraph interrupt the Approval Gate uses. The specialist node treats the interrupt as a halt, not an error.

**Halt and restart, not pause and continue.** When the owner answers, the stage re-enters from its entry node with a fresh conversation seeded from the re-rendered DNA, the same seeding path revise and reopen use. The specialist's partial work is discarded and billed. The graph gains no per-specialist subgraph.

**A cap.** A new setting, `MARKETING_OS_MAX_CLARIFICATIONS`, default 2, bounds how many times one stage may halt to ask within one run. Past the cap the run halts with an error of type `clarification` listing what is still missing, mirroring how a spent QA budget halts with type `guardrail`. It never proceeds on a guess.

**Lifecycle.** A new run and campaign status, `awaiting_clarification`. Stage progress is unchanged; the stage holding for an answer reports it as its state, the same way a stage at a gate reports `awaiting_approval`.

**Clarifications are DNA.** A Clarification is stored as a tenant-scoped question with an answer, alongside questionnaire answers, and rendered into the Brand DNA markdown under a **Clarifications** section after the questionnaire sections. Each carries the question text, the reason, the stage and campaign that asked, and who asked. Clarifications are never Required, so the DNA Gate and completeness report ignore them. Questionnaire versioning does not apply to them.

**Answering.** A new endpoint on the run accepts the answers for its pending questions, saves them as Clarifications, and resumes the run through the same mechanism approve uses. Answering a run that is not awaiting clarification is refused. The run trace gains `stage.awaiting_clarification` and `stage.clarified` events.

**Editing.** The Brand DNA read reports Clarifications as their own section; a new endpoint updates one Clarification's answer. An edit writes nothing to any campaign and marks nothing stale; staleness stays a property of deliverable versions only.

**Review.** The tenant record gains `dna_reviewed_at` and `dna_reminded_at`. A review is due when now minus reviewed-at exceeds `MARKETING_OS_DNA_REVIEW_INTERVAL`. Saving any questionnaire or Clarification answer, and a new mark-reviewed endpoint, set reviewed-at. A tenant that has never reviewed counts from when its DNA was first completed.

**Reminder loop.** One periodic task started at API startup, ticking every interval. A tick selects tenants whose review is due and whose reminded-at is older than the interval, sends one email each through the `Mailer` port, and records reminded-at. It is one loop for one job; there is no job framework, and a dedicated worker is a later decision.

**Mailer port.** A new port with two adapters: Resend, selected by `MARKETING_OS_MAILER=resend` with `MARKETING_OS_RESEND_API_KEY` (and the sender, `MARKETING_OS_MAIL_FROM`) from the environment, and a no-op that logs, the default. The recipient is the tenant's signed-in email from the identity provider.

**Home.** The Home payload gains a Decision item per campaign awaiting clarification, linking to the answer screen, and a Review item when a review is due, linking to the Brand page. The Action Queue tag palette becomes: Decision red, Review amber, Setup amber, Stale unchanged. The empty-state copy names all three reasons an item can appear.

**Guardrail.** The shared rubric gains one line: a recommendation that rests on a fact absent from the Brand DNA fails review. The stage rubrics are unchanged in this feature.

**Scripted model.** The test-only scripted model gains a mode in which one configured stage asks a fixed question on its first run and writes its deliverable on the second, so the browser suite can walk the halt and the answer without a real model.

## Testing Decisions

Tests assert what a business owner or an operator can observe: run and campaign status, the rendered DNA, API responses, emails a fake mailer received, and screens. Nothing asserts on graph internals, node names, or message lists.

- **Compiled graph**, as in the approval-gate tests: a programmable model calls the ask tool; the run halts with `awaiting_clarification`; answering and resuming re-runs the stage with a DNA carrying the Clarifications section; a model that asks past the cap halts the run with a `clarification` error; a specialist seeded after an answer sees it in its DNA. Runs on the in-memory checkpointer, with the Postgres suite covering resume across a process boundary as it does for approvals.
- **HTTP API**, as in the API and Brand DNA API tests: answering resumes the run; answering a run not awaiting clarification is refused; the DNA read shows the section; editing a Clarification changes the DNA and no campaign; the completeness report ignores Clarifications; the Home payload carries Decision and Review items; mark-reviewed and any answer save clear the Review item.
- **Reminder loop** at the API seam: the tick is called directly with a fake clock and a fake mailer; one email per due tenant, none on a second tick within the period, one again after the period; the no-op mailer sends nothing.
- **Browser suite**: with the scripted model's ask mode on a test tenant, a run halts, Home shows the red Decision item, answering from it resumes the run to its next gate, the Brand page's Clarifications tab lists and edits the answer, and a due review shows the amber Review item until Reviewed is clicked.
- **Governance docs test**: the existing guardrail-docs test covers the new shared-rubric line.

## Out of Scope

- A structured inner loop for the specialist: plan, gather, draft, self-check. That is the next slice, after the Knowledge Library and guardrails have real content.
- Knowledge Library and stage-guardrail content, including the "no email list, so build one" playbook. The harness makes the question possible; the content decides what the answer means. That is the owner's writing, running alongside this slice.
- Pausing the specialist mid-conversation and resuming with the answer as a tool result.
- WhatsApp or any channel other than email and the app.
- A dedicated scheduled worker or a generic job framework.
- Cross-campaign learning or pattern memory.
- Changing what the DNA Gate requires.
- Re-running any campaign or stage when a Clarification or DNA answer is edited.

## Further Notes

- The `.claude/` interactive layer keeps its markdown subagents unchanged. This feature lives in the compiled harness, which is the product surface (ADR-0026). A follow-up may teach the interactive orchestrator to stop and ask the operator in the same situations.
- The reviewed-at timestamp is the single source for both the email and the in-app item, so the two can never disagree about whether a review is due.
- ADR-0018's test that no questionnaire question asks for a crafted artifact should gain a sibling for the ask tool's description, so the rule is checked in both places it is stated.

## Completion

- Completed: 2026-09-11
- Commits, one branch per issue, each merged into `main`:
  - issue 01 `feat/clarifications-01-ask-and-halt` — `8d64b68`, `58c562c`, `76e3f05`; merged as `a7ac06b`
  - issue 02 `feat/clarifications-02-answer-and-continue` — `fd4af45`, `9b21ce0`; merged as `ce9a925`
  - issue 03 `feat/clarifications-03-clarifications-tab` — `32157e9`, `8c5c088`; merged as `e41d990`
  - issue 04 `feat/clarifications-04-review-due` — `b908f63`, `f722148`; merged as `390c6d9`
  - issue 05 `feat/clarifications-05-reminder-email` — `084b1fc`, `6acc6fc`, `125fedb`; merged as `3869f2d`
  - this archive: `<to be filled in>`
- Per-criterion evidence lives on the five archived issues in [issues/archive/](../issues/archive/).
- Verified at close-out on `main` at `ecbc8da`: every Implementation Decision has a home in the code — `ask_tenant` in `adapters/tools/clarify.py`; `awaiting_clarification` on run and campaign; `max_clarifications`, `dna_review_interval`, `mailer`, Resend key and sender in `config.py`; `stage.awaiting_clarification` and `stage.clarified` in `graph/nodes.py`; the `## Clarifications` section in `questionnaire/render.py`; `GET`/`POST /runs/{id}/clarifications`, `PUT /brand-dna/clarifications/{id}`, `GET`/`POST /brand-dna/review` in the API; `dna_reviewed_at` and `dna_reminded_at` on the tenant; `send_due_reminders` and `remind_on_interval` in `reminders.py`; the `Mailer` port with Resend and no-op adapters in `adapters/mail.py`; the Home tag palette (Decision red, Review and Setup amber) and three-reason empty state; the "Asks, never assumes" line in `guardrails/shared.md`; the scripted model's `MARKETING_OS_SCRIPTED_ASK_STAGE` mode; the ADR-0018 sibling test `test_the_ask_tool_states_the_questionnaire_rule`.
- `make check` (786 passed, 130 skipped) and `make test-postgres` (916 passed) pass on `main` at `ecbc8da`. `make test-e2e` passed on each issue's branch before its merge and was not re-run for this archive, which changes no code.

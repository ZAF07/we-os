# Clarifications are Brand DNA the specialist asks for

A specialist working a stage sometimes needs a fact the Brand DNA never captured — whether the business has an email list before it can plan an email channel, say. It must never infer that fact. Agents reason about campaign work from **given** facts; a fact only the business knows is asked for, and the run waits. The specialist raises the question through a tool, the stage halts, the campaign reads `awaiting_clarification`, and the business answers in the app. The answer is recorded as a **Clarification**: a question written by the specialist for that one business, answered by the business, stored as part of its Brand DNA under its own **Clarifications** section, never Required by the DNA Gate, and read by every later campaign so the same fact is asked for once.

This is a deliberate exception to [ADR-0018](0018-human-authored-dna-from-a-curated-questionnaire.md). The DNA stays human-*answered*, which is what that decision protects; what changes is that a question can now be model-written and tenant-specific rather than admin-curated and shared. The tool carries the same rule the Questionnaire does — ask only for facts the owner uniquely knows, never for positioning, channel choice, or anything the pipeline itself owes — and the shared Guardrail fails any recommendation resting on a fact absent from the DNA, so asking is cheaper for the model than guessing.

Clarifications go stale like any fact about a business, so the platform asks the business to **review** its DNA periodically: an in-process loop in the engine, on a configured interval, sends one Resend email per due tenant and the Action Queue shows the same review as a **Review** item. Both derive from one `dna_reviewed_at` timestamp, so the app and the email cannot disagree. Editing an answer, or marking the review done, resets it and reruns nothing.

## Considered options

- **A code-declared list of DNA fields per stage, checked before the specialist runs** — rejected as the primary mechanism: it duplicates the DNA Gate for structural fields and cannot see a semantic gap. The specialist is the one reasoning about what the stage needs, so the specialist asks.
- **A separate store of "tenant facts"** — rejected: the DNA is the single source of truth every recommendation is grounded in, and a second store breaks that sentence while duplicating rendering, editing, and reading paths the DNA already has.
- **Pausing the specialist's tool loop mid-conversation and resuming with the answer** — rejected for now: it needs the specialist's inner loop checkpointed as its own subgraph. Restarting the stage from the updated DNA reuses the seeding path revise and reopen already share, at the cost of one discarded partial run, which the Usage Ledger bills.
- **Deriving "review due" on read only, no scheduler** — rejected once email became the channel: an outbound reminder has to be sent by something. The scheduler is one loop for one job inside the single engine process ([ADR-0025](0025-one-campaign-one-person-and-a-single-worker.md)); a dedicated worker or job framework waits until a second job exists.
- **Reusing `awaiting_approval` for a pending question** — rejected: there is no deliverable to review, only questions to answer, and the app shows a different thing. Lifecycle gains one value; stages stay a separate axis ([ADR-0017](0017-stages-and-lifecycle-are-separate-axes.md)).

## Consequences

- The specialist batches every question it is missing into one halt, since each halt restarts the stage.
- Rounds of asking are capped per stage (`MARKETING_OS_MAX_CLARIFICATIONS`); past the cap the run halts with what is still missing, the way a spent QA budget does. It never proceeds on a guess.
- The interval, the mailer (`resend` or `noop`), and the cap are settings, so a deployment moves from a one-minute dev interval to a weekly one without a code change.
- The proprietary value of the example — "no list, so build one, and here is how" — is Knowledge Library and Guardrail content, not harness code. The harness makes the question possible; the knowledge decides what the answer means.

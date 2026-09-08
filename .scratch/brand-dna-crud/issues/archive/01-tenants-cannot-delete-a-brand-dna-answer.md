# 01 — A business cannot remove a Brand DNA answer, and a blank Save stores an empty one

Status: completed
Type: task

## Context

The Brand screen is the surface where a business **authors and revises its own
Brand DNA** — long-lived answers it owns, separate from the per-campaign details
collected when starting a campaign. Editing already works there: per-question,
in place, one answer saved at a time
(`web/src/components/brand/brand-screen.tsx:58-67`).

Two of the three CRUD operations are missing or wrong.

## Defect 1 — Save posts an empty string as an answer

`save` sends whatever is in the box, trimmed:

    await saveAnswers([{ question_id: questionId, answer: draft.trim() }]);
    // brand-screen.tsx:62

Clear the textarea, press Save, and `answer: ""` is stored as that question's
answer. `DnaAnswer.answer` is a plain `str` with no minimum length
(`agent-harness/src/marketing_os/schemas.py:466-467`), so the engine accepts it.

The projection then renders it as an empty line — `- **<field>:** ` — in the
markdown the DNA Gate reads (`questionnaire/render.py`). That is exactly the
placeholder content `.claude/rules/brand-dna.md` prohibits, and the completeness
report counts the question as answered because a row exists for it.

## Defect 2 — there is no way to remove an answer

`POST /brand-dna/answers` upserts, and `upsert` merges the incoming answers over
what is stored (`adapters/questionnaire.py:146-147`). Absence means "leave it
alone" — which is **correct** for the wizard's partial saves, and is precisely
why a removal cannot be expressed through that endpoint.

So a business that answered a question wrongly can overwrite it but never
withdraw it. The only way to make a question unanswered again is a value that
is not an answer.

## What the product should do

**Brand screen**

- Save **refuses** a blank draft: no request is sent, and the card shows that an
  answer cannot be blank and that Delete is how to remove it.
- A per-answer **Delete** button removes the answer outright. Deletion is
  explicit and never inferred from an emptied textarea.
- No confirmation modal. The screen already renders the completeness report, so
  deleting a Required answer flips the banner to name the newly missing field —
  the consequence is visible and the action is reversible by retyping.
- Required cards say up front that deleting will re-open the DNA Gate, so it is
  known before the click rather than confirmed after.

**Engine**

- `DELETE /brand-dna/answers/{question_id}` — a distinct operation, because a
  removal is a different intent from a save and should say so on the wire.
- A `remove` method on the answer store port and **both** adapters (in-memory
  and Postgres), so the contract holds wherever the store is swapped.
- Deleting re-projects the Brand DNA markdown, exactly as `upsert` does. Without
  it the projection keeps a field the answers no longer have and the gate reads
  a stale complete DNA.
- Returns the updated completeness report, symmetric with the save endpoint and
  for the same reason its docstring gives: the caller shows progress without a
  second request. Removal is when completeness changes for the worse, so the
  banner must update from the response.
- 404 for a question the published set does not ask, matching how the save
  endpoint rejects unknown question ids.
- `upsert` keeps merging, unchanged.

## Out of scope

- **The onboarding wizard.** It already filters blanks correctly — an unanswered
  question is simply absent from the payload, which is right. Its concurrent-save
  bug is [onboarding-spec-flake/01](../../onboarding-spec-flake/issues/01-onboarding-spec-depends-on-run-order.md).
- **Campaign creation.** Different workflow: every field is Required and blocks
  advancing, optional fields are omitted entirely, and the goal is submitted once.
  No partial saves, no merge, no edit/delete affordance. Nothing to change.

## Alignment

No new domain vocabulary — `dna_answers` is already documented in `CONTEXT.md`
as the source of truth with the markdown as a derived projection. Delete-then-
reproject upholds [ADR-0018](../../../docs/adr/0018-human-authored-dna-from-a-curated-questionnaire.md);
no ADR is contradicted and none is needed.

## Acceptance criteria

- [x] Save with an empty draft sends **no** request and tells the business to use
      Delete instead.
- [x] A Delete button on each answered question removes that answer.
- [x] `DELETE /brand-dna/answers/{question_id}` removes the answer, re-projects
      the Brand DNA markdown, and returns the updated completeness report.
- [x] `remove` is on the answer store port and implemented by both the in-memory
      and Postgres adapters, with tests against both.
- [x] Deleting a Required answer flips the completeness banner to name it, and
      the DNA Gate blocks a run until it is answered again.
- [x] Deleting an unknown question id answers 404.
- [x] No empty-string answer can be stored through any path.

## Completion

- Completed: 2026-09-08
- Commits:
  - `bf1c178` — the delete operation, the blank refusal, and the Brand screen affordances.
  - `0ad624f` — code-review fixes: the blank rule moved off the read model, the
    `updated_at` contract aligned across both adapters, Delete moved onto the
    collapsed card, and the banner fed from the write's own report.

### Verification

- `uv run ruff check .` — all checks passed.
- `uv run mypy src` — no issues in 68 source files.
- `uv run pytest` — 576 passed, 86 skipped.
- `MARKETING_OS_TEST_POSTGRES=1 uv run pytest tests/test_postgres.py` — the five
  Brand DNA answer-store tests pass against a real database.
- `web`: typecheck, lint, prettier and 43 unit tests clean.
- Verified in the running app on the e2e compose stack: 46 browser tests passed,
  including the two new Brand specs and the Required-banner spec.

### Notes for whoever reads this next

- The blank rule lives on `DnaAnswersUpsert` (the request body), **not** on
  `DnaAnswer`. That is deliberate: `DnaAnswer` is also the shape a stored answer
  is read back as, so validating it there made any pre-existing blank row
  unreadable and took `GET /brand-dna`, completeness and the gate down with it.
  A Postgres test writes such a row directly and reads it back, to keep that
  from regressing.
- Blank rows written by the shipped code may still exist in production data.
  Nothing breaks on them and completeness already counts them as unanswered, so
  they surface as a missing Required field rather than silently passing the
  gate. No cleanup migration was written.
- `MARKETING_OS_TEST_POSTGRES=1` also surfaces three **pre-existing** failures in
  `test_postgres.py` from `arun_campaign` signature drift. Confirmed on `main`
  at 33c1527, unrelated to this work, filed as
  [postgres-checkpoint-tests/01](../../../postgres-checkpoint-tests/issues/01-postgres-checkpoint-tests-call-a-stale-arun-campaign.md).

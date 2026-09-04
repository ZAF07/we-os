# 06 — Questionnaire → Brand DNA → DNA Gate

Status: completed
Type: task

## Parent

[PRD: we-OS SaaS foundation](../PRD.md) · [ADR-0018](../../../docs/adr/0018-human-authored-dna-from-a-curated-questionnaire.md) · [ADR-0022](../../../docs/adr/0022-brand-dna-and-the-overloaded-customer.md)

## What to build

The path by which a business gets a complete Brand DNA — the gate that currently blocks every new user.

The **admin-curated Questionnaire** is the single artifact driving three things: the onboarding wizard, the shape of the rendered Brand DNA, and what the DNA Gate enforces as Required. It is versioned in the database and editable without a deploy. Each question carries a stable id, its text, **why it is asked**, help text, input type, required/recommended, and the DNA field it populates.

The questions ask **only for facts the business owner uniquely knows** — what they sell, price point, who buys, what problems those buyers have, why customers choose them over alternatives, geography, languages, constraints, budget. Positioning, value proposition, messaging, brand voice and channel selection are **removed** from onboarding: the engine produces those and the owner approves them at the stage gates. The Brand DNA is never drafted, scraped, or guessed by a model.

Answers are stored structured and **rendered into canonical Brand DNA markdown**, which is what agents read — the structured record is the source of truth, the markdown a derived projection. The gate's existing mechanism is preserved: Required fields derive from the published question set, so adding a question tightens the gate with no code change.

Two known defects in the shipped wizard are fixed here: it never asks for **price point, geography/service area, languages, or budget range** — four Required DNA fields — so every business completing onboarding today fails Stage 0.

Publishing a new question-set version must not retroactively fail existing tenants; it surfaces the unanswered questions as an explicit prompt.

End-to-end behaviour: a new business signs in, is walked through the questionnaire, saves partway and returns, completes it, sees its Brand DNA complete, and can start a run that the gate no longer blocks.

## Acceptance criteria

- [x] The question set is stored versioned, and publishing a new version needs no deploy.
- [x] The onboarding wizard renders entirely from the published question set — questions are not hardcoded in the frontend.
- [x] Each question displays its "why we ask" and help text.
- [x] Answers render into canonical Brand DNA markdown that specialists read unchanged.
- [x] The DNA Gate derives its Required set from the published question set; adding a Required question tightens the gate with no code change.
- [x] All Required DNA fields are collected, including price point, geography/service area, languages and budget range.
- [x] No question asks for value proposition, customer promise, differentiators, brand voice as written, or channel selection.
- [x] Onboarding can be saved partway and resumed.
- [x] A completeness report names exactly which Required fields remain.
- [x] A tenant whose DNA predates a newer question-set version is prompted to answer the new questions rather than silently failing the gate.
- [x] Any Brand DNA answer can be edited later.
- [x] `uv run pytest`, `uv run ruff check .`, `uv run ruff format`, `uv run mypy src` all pass.
- [x] Verified in the running app.

## Blocked by

- [05 — Postgres: adapter, durable checkpointer, shared run registry](archive/05-postgres-adapter-durable-checkpointer-shared-registry.md)

## Completion

- Completed: 2026-09-02
- Branch: `issue-06-questionnaire-brand-dna-gate` (pushed to origin)
- Commits: `8ab93b1` (implementation), `9e70601` (code review), `07451f6` (merge)
  - `8ab93b1` — Questionnaire → Brand DNA → DNA Gate
  - `9e70601` — Address code review: version reporting, the publish path, and the prompt
  - `e37b0cd` — updated tasks status

### Evidence

- **Versioned, published without a deploy** — `questionnaires` table keyed on `version` (`agent-harness/src/marketing_os/adapters/postgres/schema.py:113`); `marketing-os publish-questionnaire --dsn --file` publishes an admin-authored JSON set, validated before it can reach a business (`entrypoints/cli.py:287`). Verified against a real containerised Postgres by `test_publishing_a_question_set_changes_what_the_gate_requires`.
- **Wizard renders from the published set** — `questionSteps(questionnaire)` derives even the wizard's steps from each question's `section`; no question is named in the frontend (`web/src/app/onboarding/page.tsx:104,191`).
- **Every question explains itself** — why-we-ask and help text are both displayed persistently, not as a placeholder that vanishes on the first keystroke (`page.tsx:67`); `test_every_seed_question_explains_itself` holds the seed to it.
- **Canonical Brand DNA markdown** — `questionnaire/render.py` emits the `### <section>` / `- **<field>:** <value>` shape of `templates/brand-dna.md`, so the gate's own field parser and every specialist prompt read it unchanged. Confirmed by parsing a rendered DNA back through `field_map`.
- **Gate derives Required from the question set** — `check_gate(..., questionnaire=...)` uses `required_dna_fields()`; publishing a set with one added Required question tightened the gate live, with no code change (`test_gate_derives_required_dna_fields_from_the_question_set`).
- **The four missing Required fields** — `q_price_point`, `q_geography`, `q_languages`, `q_budget_range` are all Required in the seed set, closing the defect that made every onboarded business fail Stage 0.
- **No crafted-artifact questions** — `test_seed_asks_no_crafted_artifact_question` fails the build if a question asks for positioning, value proposition, promise, differentiators, brand voice, or channel selection. Asking which channels a business *already* uses is a fact and stays, as Recommended.
- **Save partway and resume** — answers upsert on `(tenant_id, question_id)`; the wizard persists on every step transition and reloads what was stored.
- **Completeness names exactly what remains** — `MissingField` carries `question_id`, `field` and the question text.
- **A predating tenant is prompted** — `unanswered_new_questions` names only questions the business was never shown, and the wizard surfaces them by field name. A business that has answered nothing reports version 0 rather than the published version, which is the comparison this keys off.
- **Any answer editable later** — a second save of one question replaces just that answer and re-renders the DNA.
- **Quality gates** — 316 passed, 28 skipped; 28 Postgres conformance tests green against a containerised server; ruff, ruff format and mypy clean; frontend typecheck, eslint and prettier clean.
- **Verified in the running app** — drove the real service over HTTP: the gate's DNA issues went 8 → 0 across onboarding, publishing a v2 with a new Required question tightened it and surfaced the prompt, and an edited answer re-rendered the DNA.

### Out of scope, deliberately

The campaign-goal half of the Stage 0 gate still reports its template's unfilled fields — that is issue 10 (campaign creation). Screens other than `/onboarding` remain fixture-backed, per issues 11 and 12.

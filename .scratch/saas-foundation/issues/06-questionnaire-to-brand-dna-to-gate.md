# 06 — Questionnaire → Brand DNA → DNA Gate

Status: ready-for-agent
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

- [ ] The question set is stored versioned, and publishing a new version needs no deploy.
- [ ] The onboarding wizard renders entirely from the published question set — questions are not hardcoded in the frontend.
- [ ] Each question displays its "why we ask" and help text.
- [ ] Answers render into canonical Brand DNA markdown that specialists read unchanged.
- [ ] The DNA Gate derives its Required set from the published question set; adding a Required question tightens the gate with no code change.
- [ ] All Required DNA fields are collected, including price point, geography/service area, languages and budget range.
- [ ] No question asks for value proposition, customer promise, differentiators, brand voice as written, or channel selection.
- [ ] Onboarding can be saved partway and resumed.
- [ ] A completeness report names exactly which Required fields remain.
- [ ] A tenant whose DNA predates a newer question-set version is prompted to answer the new questions rather than silently failing the gate.
- [ ] Any Brand DNA answer can be edited later.
- [ ] `uv run pytest`, `uv run ruff check .`, `uv run ruff format`, `uv run mypy src` all pass.
- [ ] Verified in the running app.

## Blocked by

- [05 — Postgres: adapter, durable checkpointer, shared run registry](05-postgres-adapter-durable-checkpointer-shared-registry.md)

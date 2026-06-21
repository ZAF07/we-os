# Guardrails — professional QA rubrics

Human-written acceptance criteria the harness checks each stage's deliverable
against. After a specialist writes its deliverable, the QA reviewer
(`marketing_os.governance.review`) scores it against `shared.md` **plus** the
stage-specific rubric here, and the specialist iterates until it passes (or the
iteration budget is exhausted).

These files are the voice of a senior marketer / creative director setting the
bar. **Edit them freely** — they change QA behavior with no code change. Keep
each rubric as concrete, checkable bullet points (not vibes): a reviewer can only
enforce what is stated explicitly.

| File | Checked against the deliverable from stage |
|---|---|
| `shared.md` | every stage |
| `research.md` | `research.md` (market-research) |
| `brand-strategy.md` | `brand-strategy.md` (brand-strategy) |
| `campaign-strategy.md` | `campaign-strategy.md` (Marketing Director) |
| `creative-brief.md` | `creative-brief.md` (creative-director) |
| `asset-prompts.md` | `asset-prompts.md` (creative-asset-prompt) |
| `performance-plan.md` | `performance-plan.md` (performance-marketing) |

These rubrics are read-only to the agents; only the human operator edits them.

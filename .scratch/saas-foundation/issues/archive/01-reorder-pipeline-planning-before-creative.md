# 01 — Reorder the pipeline so channel planning precedes creative

Status: completed
Type: task

## Parent

[PRD: we-OS SaaS foundation](../PRD.md) · [ADR-0016](../../../docs/adr/0016-channel-planning-precedes-creative.md)

## What to build

A prefactor, delivering a real behavioural improvement on its own. The Performance Plan moves from stage 6 to stage 4, so the pipeline runs:

```
research → brand-strategy → campaign-strategy → performance-plan → creative-brief → asset-prompts
```

Today the creative brief and asset prompts are authored before any channel decision exists, so creative is briefed without knowing its Placements — aspect ratios, format, copy limits — and the performance specialist then selects channels for creative that was never scoped to them. The channel-and-spend call is also made twice: roughly by the Marketing Director at campaign strategy, then properly at the performance plan, downstream of the creative it should have informed.

After this slice, the Performance Plan stage produces the concrete channel mix, per-channel spend allocation, KPI targets **and the format requirements creative must satisfy**; the Creative Brief takes it as its prerequisite and briefs against real Placements; and Asset Prompts are platform-correct.

End-to-end behaviour: run a campaign through the full pipeline and the performance plan is written before the creative brief, and the creative brief demonstrably references the channels and placements the plan chose.

Scope: the stage order and prerequisite chain, the stage task text, and the Creative Brief and Performance Plan guardrail rubrics (the creative-brief rubric must now require the brief to honour the plan's placements). "Budget" throughout means the business's media/ad spend, not generation cost.

Do this first. It is cheap now and expensive once the frontend and stored campaigns bind to the current order.

## Acceptance criteria

- [x] The pipeline runs in the new order, and the Creative Brief's prerequisite is the Performance Plan.
- [x] Starting the Creative Brief stage before a Performance Plan exists is blocked, with the prerequisite named.
- [x] The Performance Plan stage task asks for channel mix, per-channel spend allocation, KPI targets, and the placement/format requirements for creative.
- [x] The Creative Brief stage task instructs the specialist to brief against the placements in the performance plan.
- [x] The Creative Brief guardrail rubric fails a brief that ignores the plan's placements.
- [x] A full-pipeline run with the scripted model produces deliverables in the new order.
- [x] `uv run pytest`, `uv run ruff check .`, `uv run ruff format`, `uv run mypy src` all pass.
- [x] `CONTEXT.md`'s pipeline table already reflects the new order; confirm no other doc contradicts it.

## Blocked by

None - can start immediately.
## Comments

- Implemented exactly as specified; `campaign-strategy`'s task was also reworded to "a
  rough channel direction … the performance plan will make the channel mix and spend
  allocation concrete", per ADR-0016's stage-3-keeps-the-strategic-call split.
- Contradiction sweep fixed the old order in `.claude/rules/decision-hierarchy.md`,
  `.claude/skills/new-campaign/SKILL.md`, `.claude/agents/performance-marketing.md`,
  `.claude/agents/creative-director.md`, `README.md`, `agent-harness/README.md`,
  `USAGE.md`, and `agent-harness/USAGE.md`. `CONTEXT.md` already matched.
- Rubric content is pinned by `agent-harness/tests/test_guardrail_docs.py` so the
  placement requirements can't silently drift out of the rubrics.

## Completion

- Completed: 2026-08-20
- Commit: <to be filled in manually>

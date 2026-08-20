# Sharpen the guardrail rubrics to a professional bar

Status: ready-for-human

The QA rubrics in `guardrails/*.md` are functional but flagged as needing sharpening to the standard a professional marketer would hold. Because the reviewer scores deliverables against these files at runtime (ADR-0003), tightening them raises output quality with no code change.

## What's needed

- Review and sharpen `guardrails/shared.md` and each stage rubric (`research.md`, `brand-strategy.md`, `campaign-strategy.md`, `creative-brief.md`, `asset-prompts.md`, `performance-plan.md`).
- Keep them concrete and checkable (pass/fail per rubric point), since discrepancies are fed back to specialists verbatim.

## Evidence

- `agent-harness/TODO.md` (extension point: "Guardrail rubrics: sharpen `guardrails/*.md` to professional bar").
- `agent-harness/src/marketing_os/governance/rubric.py` (`load_rubric` reads these files at review time).

## Comments

**2026-08-20.** Rubrics are now classed as admin-tunable content and move into Postgres, editable without a deploy ([ADR-0014](../../../docs/adr/0014-postgres-system-of-record-and-split-governance.md)). Sharpening the content is still the work here and is unaffected — but do it against the migrated store rather than `guardrails/*.md` if the migration has already landed. Also note the pipeline reorder ([ADR-0016](../../../docs/adr/0016-channel-planning-precedes-creative.md)): the creative-brief rubric must now require the brief to honour the placements set by the performance plan.

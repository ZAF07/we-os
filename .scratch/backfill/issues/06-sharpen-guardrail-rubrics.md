# Sharpen the guardrail rubrics to a professional bar

Status: ready-for-human

The QA rubrics in `guardrails/*.md` are functional but flagged as needing sharpening to the standard a professional marketer would hold. Because the reviewer scores deliverables against these files at runtime (ADR-0003), tightening them raises output quality with no code change.

## What's needed

- Review and sharpen `guardrails/shared.md` and each stage rubric (`research.md`, `brand-strategy.md`, `campaign-strategy.md`, `creative-brief.md`, `asset-prompts.md`, `performance-plan.md`).
- Keep them concrete and checkable (pass/fail per rubric point), since discrepancies are fed back to specialists verbatim.

## Evidence

- `agent-harness/TODO.md` (extension point: "Guardrail rubrics: sharpen `guardrails/*.md` to professional bar").
- `agent-harness/src/marketing_os/governance/rubric.py` (`load_rubric` reads these files at review time).

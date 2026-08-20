"""Repo guardrail rubrics: the checks ADR-0016 requires them to enforce.

These read the real ``guardrails/`` rubrics at the repo root (not the hermetic
fixture) because the rubric text is itself the enforced artifact: the reviewer
judges deliverables against it verbatim.
"""

from __future__ import annotations

from pathlib import Path

_GUARDRAILS_DIR = Path(__file__).resolve().parents[2] / "guardrails"


def test_creative_brief_rubric_requires_honouring_the_plans_placements():
    rubric = (_GUARDRAILS_DIR / "creative-brief.md").read_text(encoding="utf-8")
    assert "performance plan" in rubric
    assert "placement" in rubric
    assert "ignores the plan's placements fails" in rubric


def test_performance_plan_rubric_requires_placement_format_specs():
    rubric = (_GUARDRAILS_DIR / "performance-plan.md").read_text(encoding="utf-8")
    assert "Placements are specified" in rubric
    assert "aspect ratio" in rubric
    assert "copy limits" in rubric

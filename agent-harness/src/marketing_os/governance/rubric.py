"""Rubric assembly — pure, framework-free construction of the QA review rubric.

Combines the shared rubric, the stage-specific rubric, and the operating
principles into a single string the reviewer judges a deliverable against. When no
rubric files exist yet, a compact fallback derived from the core principles is
returned so the reviewer always has a bar to check against.
"""

from __future__ import annotations

from marketing_os.config import Settings
from marketing_os.governance.rules import load_operating_principles

_FALLBACK_RUBRIC = (
    "- Strategy before content. Revenue before engagement.\n"
    "- Every recommendation is evidence-based, explains why, and ties to the "
    "business objective.\n"
    "- Ground everything in the Customer DNA; no generic filler."
)


def load_rubric(settings: Settings, stage_key: str) -> str:
    """Assemble the review rubric for a stage.

    Args:
        settings: The harness settings locating the ``guardrails/`` directory.
        stage_key: The pipeline stage whose rubric is requested.

    Returns:
        The combined rubric text: the shared rubric, the stage-specific rubric,
        and the operating principles, or a compact fallback when none exist.
    """
    parts: list[str] = []
    guardrails_dir = settings.guardrails_dir
    shared = guardrails_dir / "shared.md"
    stage_rubric = guardrails_dir / f"{stage_key}.md"
    if shared.is_file():
        parts.append(shared.read_text(encoding="utf-8").strip())
    if stage_rubric.is_file():
        parts.append(stage_rubric.read_text(encoding="utf-8").strip())
    principles = load_operating_principles(settings)
    if principles:
        parts.append(principles)
    if not parts:
        parts.append(_FALLBACK_RUBRIC)
    return "\n\n---\n\n".join(parts)

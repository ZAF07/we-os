"""Editable professional rubrics (repo-root `guardrails/*.md`).

These are the human-written, *editable* quality bar — distinct from the
non-editable `hard.py` floor. The Evaluator agent scores the strategy package
against them. Editing the markdown changes the bar with no code change.
"""

from __future__ import annotations

from ..config import Settings


def load_rubric(settings: Settings, *stage_keys: str) -> str:
    """Assemble the review rubric: shared rubric + the named stage rubrics.

    Args:
        settings: Resolved settings (locates the repo-root `guardrails/` dir).
        *stage_keys: Stage rubric filenames to include (e.g. "strategy", "creative").

    Returns:
        The concatenated rubric text. Falls back to a built-in minimal bar if the
        markdown files are absent, so the Evaluator always has criteria.
    """
    gdir = settings.guardrails_dir
    parts: list[str] = []
    shared = gdir / "shared.md"
    if shared.is_file():
        parts.append(shared.read_text(encoding="utf-8").strip())
    for key in stage_keys:
        f = gdir / f"{key}.md"
        if f.is_file():
            parts.append(f.read_text(encoding="utf-8").strip())
    if not parts:
        parts.append(
            "- Grounded in the Customer DNA / evidence; no generic filler.\n"
            "- Every recommendation explains why and ties to the business objective.\n"
            "- Strategy is specific, feasible, brand-consistent, and testable."
        )
    return "\n\n---\n\n".join(parts)

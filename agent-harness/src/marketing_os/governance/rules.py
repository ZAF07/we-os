"""Load the canonical governance from `.claude/rules/*.md`.

These rule files (`decision-hierarchy.md`, `operating-principles.md`,
`customer-dna.md`) are the non-negotiable governance every specialist runs under.
They are concatenated into a single preamble that is prepended to every agent's
system prompt — the same content the Claude Code session loads each turn.
"""

from __future__ import annotations

from ..config import Settings

# Stable order so the cached prompt prefix doesn't churn between runs.
_PREFERRED_ORDER = [
    "operating-principles.md",
    "decision-hierarchy.md",
    "customer-dna.md",
]


def load_governance(settings: Settings) -> str:
    """Concatenate the rule files into the shared governance preamble."""
    rules_dir = settings.rules_dir
    if not rules_dir.is_dir():
        return ""
    files = sorted(rules_dir.glob("*.md"))
    ordered = [rules_dir / n for n in _PREFERRED_ORDER if (rules_dir / n).is_file()]
    ordered += [f for f in files if f not in ordered]

    parts = [
        "# Marketing OS — Governance (non-negotiable; applies to every step)",
        "",
        "You operate inside a decision-making system, not a content generator. The "
        "goal is revenue growth; content and assets are downstream tools. Obey the "
        "rules below at every step.",
    ]
    for f in ordered:
        parts.append("")
        parts.append(f.read_text(encoding="utf-8").strip())
    return "\n".join(parts)


def load_operating_principles(settings: Settings) -> str:
    """Just the operating principles (used by the QA reviewer)."""
    path = settings.rules_dir / "operating-principles.md"
    return path.read_text(encoding="utf-8").strip() if path.is_file() else ""

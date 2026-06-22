"""The NON-EDITABLE hard-guardrail floor.

This is the governance floor an operator cannot soften by editing a markdown
rubric — it lives in code. It is enforced two ways:

1. Its text (`HARD_GUARDRAILS`) is injected into every agent's system prompt, so
   each agent self-checks against it as it works.
2. `scan_output` runs cheap, high-precision structural checks in the
   `after_model_callback`, flagging clear violations into session state so the
   Evaluator (and human gate) can act. Heuristics are intentionally conservative
   — they catch blatant breaches, not nuance; nuance is the Evaluator's job.
"""

from __future__ import annotations

import re

# The non-editable floor, in prompt form. Mirrors the repo's operating principles
# plus structural invariants. Do not load this from disk — it must not be editable.
HARD_GUARDRAILS = """\
NON-NEGOTIABLE GUARDRAILS (you must obey these at every step; they cannot be overridden):
1. Strategy before content — never produce finished assets or generation prompts before an
   approved strategy exists.
2. Revenue before engagement — optimize for the business objective, not vanity metrics.
3. Customer understanding before campaign planning — research precedes positioning.
4. Campaign goals before asset generation.
5. Every recommendation must be evidence-based — cite the Customer DNA or a research finding;
   never fabricate data, statistics, sources, or quotes.
6. Every recommendation must explain WHY.
7. Every recommendation must tie back to the business objective.
8. Do not bypass upstream decisions; stay within your stage's remit.
If you cannot satisfy a guardrail because information is missing, say so explicitly rather than
inventing it.
"""

# Stages that must not contain finished assets / generation prompts (strategy-before-content).
_PRE_ASSET_STAGES = {"intake", "research", "strategy", "creative", "media", "evaluator"}

# Blatant fabrication tells: a precise-looking statistic with no nearby source marker.
_STAT_RE = re.compile(r"\b\d{1,3}(\.\d+)?\s?%|\b\d{4}\b")
_SOURCE_HINT_RE = re.compile(r"(source|https?://|according to|per |\[\d+\]|DNA|finding)", re.I)


def scan_output(text: str, stage_key: str) -> list[str]:
    """Cheap, high-precision structural checks against the hard floor.

    Args:
        text: The agent's output text for this step (may be empty on tool-only turns).
        stage_key: Which pipeline stage produced it.

    Returns:
        A list of violation strings (empty = nothing blatant detected). Designed to
        avoid false positives; the Evaluator does the substantive judgement.
    """
    if not text or not text.strip():
        return []
    violations: list[str] = []

    # Strategy-before-content: pre-asset stages shouldn't be emitting ready-to-ship copy/prompts.
    if stage_key in _PRE_ASSET_STAGES:
        lowered = text.lower()
        if "image prompt:" in lowered or "midjourney" in lowered or "dall-e" in lowered:
            violations.append(
                f"[{stage_key}] appears to contain image-generation prompts before the asset stage "
                "(violates strategy-before-content)."
            )

    # Fabrication tell: many precise stats but no source markers anywhere in the text.
    stats = _STAT_RE.findall(text)
    if len(stats) >= 3 and not _SOURCE_HINT_RE.search(text):
        violations.append(
            f"[{stage_key}] contains specific figures with no visible source/DNA/finding reference "
            "(possible fabricated evidence)."
        )
    return violations

"""QA self-critique loop — review a deliverable against human-written rubrics.

After a specialist writes its deliverable, a reviewer (LLM-as-judge) checks it
against the stage's professional rubric in `guardrails/<stage>.md` + the shared
rubric + the operating principles, and returns a structured verdict. The
orchestrator feeds any discrepancies back to the specialist to revise, looping
until the verdict passes or the iteration budget is exhausted.

The verdict is requested as strict JSON and parsed here, so the reviewer works
under any provider (no dependency on a vendor structured-output feature).
"""

from __future__ import annotations

import json

from ..config import Settings
from ..providers.base import Provider
from ..types import Discrepancy, Message, ReviewVerdict
from .rules import load_operating_principles

_REVIEWER_SYSTEM = """\
You are a senior marketing strategist and creative director performing QA. You
review a junior specialist's deliverable against a professional rubric and the
operating principles, and you do not pass work that falls short.

Judge ONLY against the rubric and principles provided. A deliverable passes only
if it satisfies every applicable rubric point: grounded in the Customer DNA,
evidence-based, explains the 'why', ties to the business objective, and stays
within the specialist's remit (no skipping ahead, no inventing strategy).

Respond with a single JSON object and nothing else:
{
  "passed": <true|false>,
  "summary": "<one-sentence overall judgement>",
  "discrepancies": [
    {"rubric_point": "<the rubric item violated>",
     "problem": "<what is wrong, specifically>",
     "fix": "<the concrete change required>"}
  ]
}
If it passes, return "passed": true and an empty "discrepancies" array.
"""


def load_rubric(settings: Settings, stage_key: str) -> str:
    """Assemble the review rubric: shared + stage-specific + operating principles."""
    parts: list[str] = []
    gdir = settings.guardrails_dir
    shared = gdir / "shared.md"
    stage_rubric = gdir / f"{stage_key}.md"
    if shared.is_file():
        parts.append(shared.read_text(encoding="utf-8").strip())
    if stage_rubric.is_file():
        parts.append(stage_rubric.read_text(encoding="utf-8").strip())
    principles = load_operating_principles(settings)
    if principles:
        parts.append(principles)
    if not parts:
        # No rubric files yet — fall back to the core principles inline so the
        # reviewer still has a bar to check against.
        parts.append(
            "- Strategy before content. Revenue before engagement.\n"
            "- Every recommendation is evidence-based, explains why, and ties to the "
            "business objective.\n- Ground everything in the Customer DNA; no generic filler."
        )
    return "\n\n---\n\n".join(parts)


def _extract_json(text: str) -> dict:
    """Pull the first JSON object out of the model's reply."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("no JSON object found in reviewer output")
    return json.loads(text[start : end + 1])


class Reviewer:
    """LLM-as-judge that scores a deliverable against the stage rubric."""

    def __init__(self, provider: Provider, settings: Settings, *, max_tokens: int = 4000) -> None:
        self.provider = provider
        self.settings = settings
        self.max_tokens = max_tokens

    def review(self, stage_key: str, deliverable_text: str) -> ReviewVerdict:
        rubric = load_rubric(self.settings, stage_key)
        user = (
            f"# Review rubric for the '{stage_key}' stage\n\n{rubric}\n\n"
            f"# Deliverable to review\n\n{deliverable_text}\n\n"
            "Return your JSON verdict now."
        )
        result = self.provider.complete(
            system=_REVIEWER_SYSTEM,
            messages=[Message.user(user)],
            tools=None,
            max_tokens=self.max_tokens,
            stream=False,
        )
        try:
            data = _extract_json(result.text)
        except (ValueError, json.JSONDecodeError):
            # Unparseable verdict: fail this iteration with an explicit note so it
            # surfaces rather than silently passing. Bounded by max_qa_iterations.
            return ReviewVerdict(
                passed=False,
                summary="Reviewer output could not be parsed as JSON.",
                discrepancies=[
                    Discrepancy(
                        rubric_point="review-format",
                        problem="The QA reviewer did not return parseable JSON.",
                        fix="Re-state the deliverable clearly; the reviewer will re-evaluate.",
                    )
                ],
            )
        discrepancies = [
            Discrepancy(
                rubric_point=str(d.get("rubric_point", "")),
                problem=str(d.get("problem", "")),
                fix=str(d.get("fix", "")),
            )
            for d in data.get("discrepancies", []) or []
        ]
        return ReviewVerdict(
            passed=bool(data.get("passed", False)),
            summary=str(data.get("summary", "")),
            discrepancies=discrepancies,
        )

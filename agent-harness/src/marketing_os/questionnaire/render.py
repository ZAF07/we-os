"""Renders structured answers into the canonical Brand DNA markdown agents read.

The structured answers are the source of truth; this markdown is the derived
projection (ADR-0018). It targets exactly the shape of ``templates/brand-dna.md``
— ``### <section>`` headings holding ``- **<field>:** <value>`` lines — because
that is the document every specialist prompt and the gate's field parser already
understand. Nothing about the agents changes when a business onboards through the
questionnaire instead of hand-authoring the file.

A multi-line answer is written as an indented sub-list under its label, which the
gate's field parser reads as one filled value rather than an empty one.
"""

from __future__ import annotations

from marketing_os.schemas import BrandDnaRecord, Question, Questionnaire

REQUIRED_HEADING = "## Required (the agent will not start without these)"
RECOMMENDED_HEADING = "## Recommended (sharper inputs = sharper output)"
RECOMMENDED_SECTION = "Recommended"

_PREAMBLE = (
    "> Authored by the business through the we-OS questionnaire. "
    "The structured answers are the source of truth; this file is their canonical "
    "projection, and is what the specialists read."
)


def _render_field(question: Question, answer: str) -> list[str]:
    """Render one answered question as its Brand DNA field line.

    Args:
        question: The question whose ``field`` labels the line.
        answer: The owner's answer text.

    Returns:
        The markdown lines for the field — one line for a single-line answer,
        a label plus an indented sub-list for a multi-line one.
    """
    lines = [line.strip() for line in answer.strip().splitlines() if line.strip()]
    if len(lines) == 1:
        return [f"- **{question.field}:** {lines[0]}"]
    return [f"- **{question.field}:**", *[f"  - {line.lstrip('-* ')}" for line in lines]]


def render_brand_dna(
    questionnaire: Questionnaire, record: BrandDnaRecord, *, business_name: str
) -> str:
    """Render a business's answers as canonical Brand DNA markdown.

    Unanswered questions are omitted rather than written as empty labels, so the
    rendered document never carries a placeholder the gate would have to
    special-case: a missing Required field is missing, plainly.

    Args:
        questionnaire: The published question set defining the fields and their
            order and sections.
        record: The business's stored answers.
        business_name: The business's display name, used in the title.

    Returns:
        The Brand DNA markdown, ready to write to the tenant's ``dna.md``.
    """
    required_lines: list[str] = []
    recommended_lines: list[str] = []
    current_section: str | None = None

    for question in questionnaire.questions:
        answer = record.answer_for(question.id)
        if not answer or not answer.strip():
            continue
        is_recommended = question.section == RECOMMENDED_SECTION
        target = recommended_lines if is_recommended else required_lines
        if not is_recommended and question.section != current_section:
            current_section = question.section
            target.extend(["", f"### {question.section}"])
        target.extend(_render_field(question, answer))

    body = [f"# Brand DNA — {business_name}", "", _PREAMBLE, "", REQUIRED_HEADING]
    body.extend(required_lines)
    if recommended_lines:
        body.extend(["", RECOMMENDED_HEADING, "", *recommended_lines])
    return "\n".join(body).strip() + "\n"

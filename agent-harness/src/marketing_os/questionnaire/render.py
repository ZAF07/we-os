"""Renders structured answers into the canonical Brand DNA markdown agents read.

The structured answers are the source of truth; this markdown is the derived
projection (ADR-0018). It targets exactly the shape of ``templates/brand-dna.md``
— ``### <section>`` headings holding ``- **<field>:** <value>`` lines — because
that is the document every specialist prompt and the gate's field parser already
understand. Nothing about the agents changes when a business onboards through the
questionnaire instead of hand-authoring the file.

The line format itself — and the multi-line and placeholder rules that make a
render read back as one filled value — belongs to
:mod:`marketing_os.markdown`, which the gate parses with. Writing and reading
agree because they are the same module.
"""

from __future__ import annotations

from marketing_os.markdown import render_field
from marketing_os.schemas import BrandDnaRecord, Questionnaire

REQUIRED_HEADING = "## Required (the agent will not start without these)"
RECOMMENDED_HEADING = "## Recommended (sharper inputs = sharper output)"
RECOMMENDED_SECTION = "Recommended"

BUSINESS_NAME_QUESTION = "q_business_name"

_PREAMBLE = (
    "> Authored by the business through the we-OS questionnaire. "
    "The structured answers are the source of truth; this file is their canonical "
    "projection, and is what the specialists read."
)


def _title_for(record: BrandDnaRecord, fallback: str) -> str:
    """Return the name the Brand DNA titles itself with.

    The structured answers are the source of truth and this markdown their
    projection (ADR-0018), so the business's own answer is authoritative over the
    identity provider's organization name.

    Args:
        record: The business's stored answers.
        fallback: The name to use when the Business name question is unanswered.

    Returns:
        The answered business name, or the fallback.
    """
    answer = record.answer_for(BUSINESS_NAME_QUESTION)
    if answer and answer.strip():
        return answer.strip().splitlines()[0].strip()
    return fallback


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
        business_name: The name to title the document with when the business has
            not answered the Business name question — the verified identity's
            organization name. The answer wins when there is one, so editing it
            moves the heading rather than leaving a second, stale name behind.

    Returns:
        The Brand DNA markdown, ready to write to the tenant's ``dna.md``.
    """
    title = _title_for(record, business_name)
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
        target.extend(render_field(question.field, answer))

    body = [f"# Brand DNA — {title}", "", _PREAMBLE, "", REQUIRED_HEADING]
    body.extend(required_lines)
    if recommended_lines:
        body.extend(["", RECOMMENDED_HEADING, "", *recommended_lines])
    return "\n".join(body).strip() + "\n"

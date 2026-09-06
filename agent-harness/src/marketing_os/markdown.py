"""The `- **Label:** value` field format, and the one place it is agreed.

This line shape is the seam between what a business answers and what the system
reads: the Questionnaire renders it (ADR-0018), the Brand DNA gate and the
campaign goal parse it, and a hand-authored template uses it too. Governance as
markdown is deliberate (ADR-0003) — but a format agreed in three docstrings and
enforced nowhere is a round trip nothing guarantees, so it is written down here
once and the three consumers call in.

Two rules the format carries, stated here rather than re-explained at each
reader:

**Multi-line values.** A field's value is the text on its own line *plus* any
following lines — indented sub-bullets, numbered lists, continuation prose — up
to the next field line or the next markdown heading. A label whose value is
written as a list underneath it is therefore filled, not empty, which is what
lets the Questionnaire render a multi-line answer as a sub-list and the gate
still count it.

Those continuation lines come back as the business wrote them, not as the
markdown that carried them: the indentation and the ``- `` bullet
:func:`render_field` adds are stripped on the way in, so what a business
answered survives the round trip. Readers that need the answer — the audience
segments a campaign may target, say — would otherwise each strip the markup
again, and one of them would eventually strip it differently.

**Placeholders.** A value that is empty, or is a single angle-bracket token like
``<name>``, is unfilled. That is how a template ships a blank a business has yet
to replace, and how the gate tells "not answered" from "answered".

Top level, beside :mod:`~marketing_os.schemas` and :mod:`~marketing_os.ports`,
because the three consumers are sibling packages that do not import one another.
Shared vocabulary lives at the root; packages sit above it.
"""

from __future__ import annotations

import re

_FIELD_RE = re.compile(r"^\s*-\s*\*\*(.+?):\*\*\s*(.*)$")
"""Matches one ``- **Label:** value`` line, capturing the label and the value."""

_PLACEHOLDER_RE = re.compile(r"^<[^>]*>$")


def render_field(label: str, value: str) -> list[str]:
    """Render one labelled field, as one line or as a label with a sub-list.

    A single-line value sits on the label's own line. A multi-line one becomes an
    indented sub-list under the label, which :func:`parse_fields` reads back as
    one filled value — the round trip the format exists to guarantee.

    Args:
        label: The field's label, written between the bold markers.
        value: The value to render; blank lines are dropped and each remaining
            line becomes a sub-bullet when there is more than one.

    Returns:
        The markdown lines for the field.
    """
    lines = [line.strip() for line in value.strip().splitlines() if line.strip()]
    if not lines:
        return [f"- **{label}:**"]
    if len(lines) == 1:
        return [f"- **{label}:** {lines[0]}"]
    return [f"- **{label}:**", *[f"  - {line.lstrip('-* ')}" for line in lines]]


def parse_fields(document: str) -> dict[str, str]:
    """Map every labelled field in a document to its value.

    Args:
        document: The markdown to read.

    Returns:
        Each label mapped to its value, multi-line values joined with newlines
        and stripped. A label written more than once keeps its last value.
    """
    values: dict[str, str] = {}
    for label, value in walk_fields(document):
        values[label] = value
    return values


def walk_fields(document: str) -> list[tuple[str, str]]:
    """Return every labelled field in document order, with its full value.

    The one implementation of the section walk. A field's value runs to the next
    field line or the next markdown heading, so a value written as a list under
    its label arrives whole.

    Args:
        document: The markdown to read.

    Returns:
        ``(label, value)`` pairs in the order they appear, values stripped.
    """
    fields: list[tuple[str, str]] = []
    label: str | None = None
    parts: list[str] = []

    def flush() -> None:
        if label is not None:
            fields.append((label, "\n".join(parts).strip()))

    for line in document.splitlines():
        match = _FIELD_RE.match(line)
        if match:
            flush()
            label = match.group(1).strip()
            parts = [match.group(2)]
        elif line.lstrip().startswith("#"):
            flush()
            label, parts = None, []
        elif label is not None:
            parts.append(_continuation(line))
    flush()
    return fields


def _continuation(line: str) -> str:
    """Strip the markup a continuation line is carried by, keeping its text.

    A line that is nothing but markup — a bare ``-`` bullet, a ``***`` rule —
    carries no answer, so it comes back empty rather than as its own markup. A
    field whose value is only such lines is therefore unfilled, which is what
    stops an empty bullet counting as a filled Required field at the gate.

    Args:
        line: One line following a field's label.

    Returns:
        The line's own text, without its indentation or list bullet; empty when
        the line carried no text of its own.
    """
    return line.strip().lstrip("-*").strip()


def is_placeholder(value: str) -> bool:
    """Report whether a value is unfilled.

    Args:
        value: The value to judge.

    Returns:
        ``True`` when the value is blank or a single ``<...>`` token a business
        has yet to replace.
    """
    stripped = value.strip()
    return stripped == "" or bool(_PLACEHOLDER_RE.match(stripped))


def labels_under_heading(document: str, heading: str) -> list[str]:
    """Return the field labels under one ``## `` section of a document.

    The section runs to the next ``## `` heading, so ``###`` subsections stay
    inside it — a template groups Required fields under sub-headings and they
    are all still Required.

    Args:
        document: The markdown to read.
        heading: The section's heading text, matched as a prefix after ``## ``
            (for example ``"Required"``).

    Returns:
        The labels in document order, empty when the section is absent.
    """
    prefix = f"## {heading}"
    labels: list[str] = []
    inside = False
    for line in document.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            inside = True
            continue
        if inside and stripped.startswith("## "):
            break
        if inside:
            match = _FIELD_RE.match(line)
            if match:
                labels.append(match.group(1).strip())
    return labels

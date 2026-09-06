"""The `- **Label:** value` field format: what it writes, it must read back.

This line shape is the seam between what a business answers and what the system
reads (ADR-0018): the Questionnaire renders it, and the Brand DNA gate and the
campaign goal parse it. The round trip was previously guaranteed by nothing —
three modules agreed on it in prose. These tests are the guarantee.

The round trip is asserted twice over. The generated property says it holds for
arbitrary labels and values; the table beside it names the cases that have
actually bitten — punctuation a parser could mistake for markup, an answer the
business already wrote as a list — so a regression report says which rule broke
rather than only that some input did.
"""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from marketing_os.markdown import (
    is_placeholder,
    labels_under_heading,
    parse_fields,
    render_field,
    walk_fields,
)

ROUND_TRIP_VALUES = [
    pytest.param("Acme Climbing Gym", id="plain"),
    pytest.param("Urban 22-35 beginners", id="hyphenated"),
    pytest.param("$18–24 a bag", id="currency-and-en-dash"),
    pytest.param("We ship within a day of roasting.", id="sentence"),
    pytest.param("A value with **bold** inside it", id="bold-markers-in-value"),
    pytest.param("A value with a : colon", id="colon"),
    pytest.param("Commuters\nStudents\nWeekend climbers", id="multi-line"),
    pytest.param("  Padded  ", id="surrounding-whitespace"),
]

NORMALISED_VALUES = [
    pytest.param("- Commuters\n- Students", "Commuters\nStudents", id="already-bulleted"),
    pytest.param("One\n\nTwo", "One\nTwo", id="blank-line-between"),
    pytest.param("  -  \n  Students", "Students", id="an-empty-bullet-carries-nothing"),
    pytest.param("Students\n***", "Students", id="a-trailing-rule-carries-nothing"),
]
"""Values the format deliberately tidies on the way through, and what they become.

The format carries a business's answer, not the markdown it arrived in: a list
the business already bulleted is the same answer as one it did not, and a line
that is only markup is not an answer at all. Each is asserted as its stated
result rather than left to whatever the parser happens to do.
"""

ROUND_TRIP_LABELS = [
    pytest.param("Business name", id="plain"),
    pytest.param("Primary segment(s)", id="parentheses"),
    pytest.param("Campaign-specific constraints", id="hyphenated"),
    pytest.param("What do your main products or services cost?", id="question"),
]


@pytest.mark.parametrize("value", ROUND_TRIP_VALUES)
@pytest.mark.parametrize("label", ROUND_TRIP_LABELS)
def test_a_rendered_field_parses_back_to_the_value_it_was_given(label: str, value: str) -> None:
    """Render then parse is the identity, modulo the whitespace stripping.

    This is the contract the Questionnaire and the gate both depend on: an
    answer a business gave must survive being written to markdown and read back,
    or the gate refuses work the business actually did.
    """
    document = "\n".join(render_field(label, value))

    parsed = parse_fields(document)

    assert parsed[label] == value.strip()


@pytest.mark.parametrize(("value", "expected"), NORMALISED_VALUES)
def test_a_value_carrying_markup_comes_back_as_the_answer_inside_it(
    value: str, expected: str
) -> None:
    """The format normalises presentation, and these are the cases it changes."""
    document = "\n".join(render_field("Audience", value))

    assert parse_fields(document)["Audience"] == expected


def test_an_empty_bullet_is_not_a_filled_field() -> None:
    """A bullet with nothing in it must not satisfy a Required question.

    The gate asks only whether a value is a placeholder, so a continuation line
    that came back as literal ``-`` would pass a Required field the business
    never answered.
    """
    document = "- **Audience:**\n  - \n  -"

    assert is_placeholder(parse_fields(document)["Audience"])


def test_a_multi_line_value_is_one_filled_field_not_an_empty_one() -> None:
    """The rule that makes a sub-list count as an answer rather than a blank."""
    document = "\n".join(render_field("Audience", "Commuters\nStudents"))

    assert document.splitlines()[0] == "- **Audience:**"
    assert not is_placeholder(parse_fields(document)["Audience"])


def test_a_value_runs_to_the_next_field_or_heading() -> None:
    document = "\n".join(
        [
            "## Business",
            "- **Name:** Acme",
            "- **Audience:**",
            "  - Commuters",
            "  - Students",
            "## Reach",
            "- **Where:** Australia",
        ]
    )

    parsed = parse_fields(document)

    assert parsed["Name"] == "Acme"
    assert parsed["Audience"] == "Commuters\nStudents"
    assert parsed["Where"] == "Australia"


def test_fields_come_back_in_document_order() -> None:
    document = "\n".join(
        ["- **First:** a", "- **Second:** b", "- **Third:** c"],
    )

    assert [label for label, _ in walk_fields(document)] == ["First", "Second", "Third"]


@pytest.mark.parametrize("value", ["", "   ", "<name>", "<>", "  <what you sell>  "])
def test_an_unfilled_value_is_a_placeholder(value: str) -> None:
    assert is_placeholder(value)


@pytest.mark.parametrize("value", ["Acme", "a < b", "<name> and more", "10 < 20 > 5"])
def test_a_filled_value_is_not_a_placeholder(value: str) -> None:
    """Only a value that is *entirely* one angle-bracket token is unfilled."""
    assert not is_placeholder(value)


def test_labels_are_read_from_the_named_section_only() -> None:
    document = "\n".join(
        [
            "## Required (the agent will not start without these)",
            "- **Business name:** <name>",
            "### Audience",
            "- **Primary segment(s):** <segments>",
            "## Recommended (sharper inputs = sharper output)",
            "- **Tone:** <tone>",
        ]
    )

    assert labels_under_heading(document, "Required") == ["Business name", "Primary segment(s)"]
    assert labels_under_heading(document, "Recommended") == ["Tone"]


def test_a_subsection_stays_inside_its_section() -> None:
    """``###`` groups Required fields; they are all still Required."""
    document = "\n".join(
        ["## Required", "### Business", "- **Name:** <name>", "### Reach", "- **Where:** <where>"]
    )

    assert labels_under_heading(document, "Required") == ["Name", "Where"]


def test_an_absent_section_has_no_labels() -> None:
    assert labels_under_heading("- **Name:** Acme", "Required") == []


def test_a_label_written_twice_keeps_its_last_value() -> None:
    parsed = parse_fields("- **Name:** first\n- **Name:** second")

    assert parsed["Name"] == "second"


# --- The generated property -----------------------------------------------

LABELS = st.text(
    alphabet=st.characters(blacklist_categories=("Cc", "Cs"), blacklist_characters="\n\r"),
    min_size=1,
    max_size=60,
).filter(lambda label: label.strip() == label and label.strip() != "" and ":**" not in label)

LINES = (
    st.text(
        alphabet=st.characters(blacklist_categories=("Cc", "Cs"), blacklist_characters="\n\r"),
        min_size=1,
        max_size=60,
    )
    .map(str.strip)
    .filter(lambda line: line != "" and line.lstrip("-*").strip() == line)
)
"""Lines carrying an answer, rather than the markdown an answer can arrive in.

Lines that are only markup, or that lead with a bullet, are normalised by design
— :data:`NORMALISED_VALUES` pins each of those as its stated result. Excluding
them here is what lets this property assert plain equality, so it checks the
parser rather than agreeing with it.
"""

VALUES = st.lists(LINES, min_size=0, max_size=6).map("\n".join)


@given(label=LABELS, value=VALUES)
def test_render_then_parse_returns_the_value_for_any_label_and_answer(
    label: str, value: str
) -> None:
    """Whatever a business answers, the document must give it back.

    The guarantee the format exists for and previously had nothing behind it: if
    this fails, the Questionnaire wrote something the gate reads differently, and
    a business is refused for work it did.
    """
    document = "\n".join(render_field(label, value))

    parsed = parse_fields(document)

    assert parsed.get(label, "") == value


@given(label=LABELS)
def test_a_field_rendered_with_no_answer_reads_as_unfilled(label: str) -> None:
    """An unanswered question must be missing plainly, not filled with markup."""
    document = "\n".join(render_field(label, ""))

    assert is_placeholder(parse_fields(document)[label])

"""The tier names, known in two languages and pointing at each other (ADR-0027).

The web app owns the tiers — names, prices, credits — because the pages that
show them are public and make no engine call. The engine knows the names alone,
to validate what a business records against its tenant. Two lists in two
languages can drift, and a drift here is a silent 422 at the one moment a new
business is being created, so this pins them together.
"""

from __future__ import annotations

import re
from pathlib import Path

from marketing_os.schemas import RECOMMENDED_TIER, TIER_NAMES

REPO = Path(__file__).resolve().parents[2]
WEB_TIER_MODULE = REPO / "web" / "src" / "lib" / "tiers.ts"
ENGINE_SOURCE = REPO / "agent-harness" / "src" / "marketing_os"


def _web_tiers() -> list[tuple[str, bool]]:
    """Read the tiers the web app defines, in order, with whether each is highlighted.

    Returns:
        Each tier's lowercase name and its ``highlighted`` flag.
    """
    source = WEB_TIER_MODULE.read_text(encoding="utf-8")
    entries = re.findall(r'name: "(\w+)",.*?highlighted: (true|false)', source, re.DOTALL)
    return [(name.lower(), flag == "true") for name, flag in entries]


def test_the_engine_knows_the_same_tiers_as_the_web_app_in_the_same_order() -> None:
    assert tuple(name for name, _ in _web_tiers()) == TIER_NAMES


def test_the_recommended_tier_is_the_one_the_web_app_highlights() -> None:
    highlighted = [name for name, flag in _web_tiers() if flag]

    assert highlighted == [RECOMMENDED_TIER]


def test_the_tier_names_are_lowercase_query_parameter_values() -> None:
    # The tier travels from the tier card to the engine as a query parameter
    # holding the lowercase name, so the engine's spelling is the lowercase one.
    assert all(name == name.lower() for name in TIER_NAMES)


def test_the_tier_definition_is_the_only_place_a_tier_is_named_on_the_engine_side() -> None:
    # A tier hardcoded anywhere else would be a quoted string, and it would be
    # the recommended one — "operator" and "command" are ordinary words this
    # codebase uses in prose, and so is "strategist" in a specialist's prompt,
    # which is why the search is for the name as a literal.
    literal = re.compile(rf"""["']{RECOMMENDED_TIER}["']""")
    named_elsewhere = [
        path.relative_to(ENGINE_SOURCE)
        for path in ENGINE_SOURCE.rglob("*.py")
        if path.name != "schemas.py" and literal.search(path.read_text(encoding="utf-8"))
    ]

    assert named_elsewhere == []

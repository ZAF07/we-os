"""Write-scope unit tests: path-escape, write-prefix, and slug-scoped guards.

These exercise :func:`validate_campaign_write` directly, without the graph or a
model, so the write-scoping rules stay covered at the level they are enforced.
The validated path is what the write tool hands the document store.
"""

from __future__ import annotations

import pytest

from marketing_os.adapters.tools.scope import validate_campaign_write
from marketing_os.errors import ToolError


def test_matching_slug_returns_the_canonical_document_path() -> None:
    assert (
        validate_campaign_write("campaigns/coast/strategy.md", "coast")
        == "campaigns/coast/strategy.md"
    )


def test_off_slug_path_is_rejected_naming_both_slugs() -> None:
    with pytest.raises(ToolError) as exc:
        validate_campaign_write("campaigns/coost/strategy.md", "coast")
    message = str(exc.value)
    assert "coost" in message
    assert "this run's slug is 'coast'" in message
    assert "verbatim" in message


def test_path_outside_campaigns_is_rejected() -> None:
    with pytest.raises(ToolError) as exc:
        validate_campaign_write("knowledge/frameworks.md", "coast")
    assert "only permitted under" in str(exc.value)


def test_traversal_out_of_campaigns_is_rejected() -> None:
    with pytest.raises(ToolError) as exc:
        validate_campaign_write("campaigns/coast/../../knowledge/x.md", "coast")
    assert "only permitted under" in str(exc.value)


def test_escaping_the_repository_root_is_rejected() -> None:
    with pytest.raises(ToolError) as exc:
        validate_campaign_write("../outside.md", "coast")
    assert "escapes the repository root" in str(exc.value)


def test_absolute_path_is_rejected() -> None:
    with pytest.raises(ToolError) as exc:
        validate_campaign_write("/etc/passwd", "coast")
    assert "escapes the repository root" in str(exc.value)


def test_write_without_slug_is_scoped_only_to_campaigns() -> None:
    assert validate_campaign_write("campaigns/anything/x.md", None) == "campaigns/anything/x.md"

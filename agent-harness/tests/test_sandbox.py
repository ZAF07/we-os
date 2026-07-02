"""Sandbox unit tests: path-escape, write-prefix, and slug-scoped write guards.

These exercise :class:`FilesystemSandbox` directly, without the graph or a model,
so the path-scoping rules stay covered at the level they are enforced.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from marketing_os.adapters.tools.sandbox import FilesystemSandbox
from marketing_os.errors import ToolError


def _sandbox(tmp_path: Path) -> FilesystemSandbox:
    """Build a sandbox rooted at a temp dir with the default campaigns prefix.

    Args:
        tmp_path: The pytest temporary directory.

    Returns:
        A sandbox permitting writes under ``campaigns/``.
    """
    return FilesystemSandbox(tmp_path, write_prefixes=["campaigns"])


def test_slug_scoped_write_accepts_matching_slug(tmp_path: Path) -> None:
    sandbox = _sandbox(tmp_path)
    result = sandbox.write("campaigns/coast/strategy.md", "# Strategy", slug="coast")
    assert (tmp_path / "campaigns" / "coast" / "strategy.md").is_file()
    assert "strategy.md" in result


def test_slug_scoped_write_rejects_off_slug_path(tmp_path: Path) -> None:
    sandbox = _sandbox(tmp_path)
    with pytest.raises(ToolError) as exc:
        sandbox.write("campaigns/coost/strategy.md", "# Strategy", slug="coast")
    message = str(exc.value)
    assert "coost" in message
    assert "this run's slug is 'coast'" in message
    assert "verbatim" in message
    assert not (tmp_path / "campaigns" / "coost").exists()


def test_slug_scoped_write_still_rejects_outside_campaigns(tmp_path: Path) -> None:
    sandbox = _sandbox(tmp_path)
    with pytest.raises(ToolError) as exc:
        sandbox.write("knowledge/frameworks.md", "# X", slug="coast")
    assert "only permitted under" in str(exc.value)
    assert not (tmp_path / "knowledge").exists()


def test_write_without_slug_is_unscoped(tmp_path: Path) -> None:
    sandbox = _sandbox(tmp_path)
    sandbox.write("campaigns/anything/x.md", "# X")
    assert (tmp_path / "campaigns" / "anything" / "x.md").is_file()

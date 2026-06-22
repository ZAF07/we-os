"""Per-agent config + tool assembly: the allowlist is authoritative."""

from __future__ import annotations

from pathlib import Path

from google.adk.tools import FunctionTool, LongRunningFunctionTool

from marketing_os.agents import load_registry
from marketing_os.tools import FilesystemTools, WebBrowser, build_tools


def test_registry_loads_all_stages(settings):
    reg = load_registry(settings)
    assert {"intake", "research", "strategy", "creative", "media", "evaluator",
            "execution", "performance"} <= set(reg.agents)
    # Research is the web-capable agent; evaluator has no tools (pure judgement).
    assert "open_page" in reg.agents["research"].tools
    assert reg.agents["evaluator"].tools == []
    # Human checks are OFF by default everywhere.
    assert all(not c.human_check for c in reg.agents.values())
    assert reg.approval_enabled is False


def _tool_names(tools) -> set[str]:
    return {getattr(t, "name", getattr(t, "__name__", "?")) for t in tools}


def test_allowlist_withholds_unlisted_tools():
    fs, br = FilesystemTools(Path("/Users/z/we-os")), WebBrowser()
    tools = build_tools(["read_file", "recall"], fs=fs, browser=br)
    names = _tool_names(tools)
    assert "read_file" in names and "recall" in names
    # Not requested -> never handed to the agent, so it cannot call it.
    assert "write_file" not in names
    assert "open_page" not in names


def test_confirm_wraps_with_confirmation_and_human_check_attaches_approval():
    fs, br = FilesystemTools(Path("/Users/z/we-os")), WebBrowser()
    tools = build_tools(
        ["read_file", "write_file"], fs=fs, browser=br,
        confirm=["write_file"], human_check=True,
    )
    by_name = {getattr(t, "name", getattr(t, "__name__", "?")): t for t in tools}
    # write_file is wrapped to require confirmation (ADK stores it as _require_confirmation).
    assert isinstance(by_name["write_file"], FunctionTool)
    assert getattr(by_name["write_file"], "_require_confirmation", False)
    # human_check attaches the long-running approval tool.
    assert any(isinstance(t, LongRunningFunctionTool) for t in tools)

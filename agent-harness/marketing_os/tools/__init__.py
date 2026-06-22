"""Per-agent tool assembly.

`build_tools` turns an agent's capability allowlist (from agents.yaml) into the
concrete list of ADK tools it may call. This is where **per-agent tool access**
and the **per-tool human-confirmation** configuration are enforced: a capability
not in the allowlist is simply never handed to the agent, so it cannot call it.

Capability names (the allowlist vocabulary):
  filesystem : read_file, write_file, list_files, search_files
  browser    : open_page, read_page, get_links, click_link, open_in_new_tab,
               list_tabs, switch_tab, go_back
  memory     : recall, remember, load_memory
"""

from __future__ import annotations

from typing import Any

from google.adk.tools import FunctionTool, load_memory

from .approval import approval_tool
from .browser import WebBrowser
from .filesystem import FilesystemTools
from .memory_tools import recall, remember

__all__ = ["FilesystemTools", "WebBrowser", "build_tools"]


def _capability_map(fs: FilesystemTools, browser: WebBrowser) -> dict[str, Any]:
    """Build the full capability-name -> tool/callable map for a run."""
    caps: dict[str, Any] = {}
    caps.update(fs.as_tools())  # read_file, write_file, list_files, search_files
    for method in browser.as_tools():  # open_page, click_link, ...
        caps[method.__name__] = method
    caps["recall"] = recall
    caps["remember"] = remember
    caps["load_memory"] = load_memory  # ADK builtin tool object
    return caps


def build_tools(
    allowed: list[str],
    *,
    fs: FilesystemTools,
    browser: WebBrowser,
    confirm: list[str] | None = None,
    human_check: bool = False,
) -> list[Any]:
    """Resolve an agent's allowed capabilities into ADK tool objects.

    Args:
        allowed: Capability names this agent may use (others are withheld).
        fs: The run's filesystem tools.
        browser: The run's web browser.
        confirm: Capabilities to wrap with ADK's built-in human confirmation
            (the model's call is gated until a human confirms).
        human_check: If True, also attach the long-running ``request_human_approval``
            tool so the agent can request explicit sign-off before finishing.

    Returns:
        A list of ADK tools/callables ready for ``LlmAgent(tools=...)``.

    Raises:
        KeyError-safe: unknown capability names are ignored with no tool added.
    """
    caps = _capability_map(fs, browser)
    confirm_set = set(confirm or [])
    tools: list[Any] = []
    for name in allowed:
        target = caps.get(name)
        if target is None:
            continue  # unknown capability: silently withhold (allowlist is authoritative)
        if name in confirm_set and name != "load_memory":
            tools.append(FunctionTool(target, require_confirmation=True))
        else:
            tools.append(target)
    if human_check:
        tools.append(approval_tool())
    return tools

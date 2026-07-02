"""Tool assembly — map an agent's declared capabilities to LangChain tools."""

from __future__ import annotations

from langchain_core.tools import BaseTool

from marketing_os.adapters.tools.filesystem import filesystem_tools
from marketing_os.adapters.tools.sandbox import FilesystemSandbox
from marketing_os.adapters.tools.websearch import NoopWebSearch, WebSearchTool, web_tools
from marketing_os.adapters.tools.websearch_playwright import PlaywrightWebSearch

__all__ = [
    "FilesystemSandbox",
    "WebSearchTool",
    "NoopWebSearch",
    "PlaywrightWebSearch",
    "build_tools",
]


def build_tools(
    declared_tools: list[str],
    *,
    sandbox: FilesystemSandbox,
    web_backend: WebSearchTool | None = None,
) -> list[BaseTool]:
    """Assemble the concrete tools an agent is granted from its declared capabilities.

    Args:
        declared_tools: Capability names from the agent frontmatter, for example
            ``["Read", "Grep", "Glob", "Write", "WebSearch", "WebFetch"]``.
        sandbox: The filesystem sandbox the filesystem tools operate through.
        web_backend: The web backend to use when the agent declares web tools;
            defaults to :class:`NoopWebSearch`.

    Returns:
        The list of LangChain tools the agent may call.
    """
    declared = set(declared_tools)
    available: dict[str, BaseTool] = {}
    available.update(filesystem_tools(sandbox, include_write="Write" in declared))
    if declared & {"WebSearch", "WebFetch"}:
        available.update(web_tools(web_backend or NoopWebSearch()))
    return [tool for capability, tool in available.items() if capability in declared]

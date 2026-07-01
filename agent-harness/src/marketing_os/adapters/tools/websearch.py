"""Web search/fetch tool interface, a default no-op stub, and ``@tool`` adapters.

Web access is pluggable: implement :class:`WebSearchTool` (see
``websearch_playwright.py`` for the Playwright skeleton) and pass it to
:func:`web_tools`. Until a real backend is wired in, :class:`NoopWebSearch` is
used so ``market-research`` and ``performance-marketing`` run without crashing —
they are simply told that search is off.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from langchain_core.tools import BaseTool, tool


class WebSearchTool(ABC):
    """Pluggable web backend providing search and fetch."""

    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> str:
        """Return a readable, source-attributed result list for a query.

        Args:
            query: The search query.
            max_results: The maximum number of results to return.

        Returns:
            A readable, source-attributed result list.
        """

    @abstractmethod
    def fetch(self, url: str) -> str:
        """Return the readable text content of a URL.

        Args:
            url: The URL to fetch.

        Returns:
            The readable text content of the page.
        """


class NoopWebSearch(WebSearchTool):
    """Default backend with no live web access, returning an honest message."""

    _MSG = (
        "Web search is not configured. Ground findings in the Customer DNA and "
        "state explicitly where external data would be needed but is unavailable."
    )

    def search(self, query: str, max_results: int = 5) -> str:
        """Return the unavailable message.

        Args:
            query: The search query (ignored).
            max_results: The result count (ignored).

        Returns:
            The configured unavailable message.
        """
        return self._MSG

    def fetch(self, url: str) -> str:
        """Return the unavailable message.

        Args:
            url: The URL (ignored).

        Returns:
            The configured unavailable message.
        """
        return self._MSG


def web_tools(backend: WebSearchTool) -> dict[str, BaseTool]:
    """Build web tools keyed by Claude-style capability name.

    Args:
        backend: The web backend the tools delegate to.

    Returns:
        A mapping of capability name (``WebSearch``, ``WebFetch``) to the tool.
    """

    @tool(parse_docstring=True)
    def web_search(query: str, max_results: int = 5) -> str:
        """Search the web for current, source-attributed information.

        Args:
            query: The search query.
            max_results: The maximum number of results to return.

        Returns:
            A readable, source-attributed result list.
        """
        return backend.search(query, max_results)

    @tool(parse_docstring=True)
    def web_fetch(url: str) -> str:
        """Fetch and return the readable text content of a URL.

        Args:
            url: The URL to fetch.

        Returns:
            The readable text content of the page.
        """
        return backend.fetch(url)

    return {"WebSearch": web_search, "WebFetch": web_fetch}

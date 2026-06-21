"""Web search/fetch tool interface + a default no-op stub.

Web access is pluggable: implement `WebSearchTool` (see `websearch_playwright.py`
for the Playwright skeleton you'll fill in) and pass it to the registry. Until a
real implementation is wired in, `NoopWebSearch` is used so `market-research` and
`performance-marketing` run without crashing — they just get told search is off.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .registry import Tool


class WebSearchTool(ABC):
    """Pluggable web backend. Implementations provide search + fetch."""

    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> str:
        """Return a readable, source-attributed result list for `query`."""

    @abstractmethod
    def fetch(self, url: str) -> str:
        """Return the readable text content of `url`."""


class NoopWebSearch(WebSearchTool):
    """Default: no live web access. Returns an honest 'unavailable' message."""

    _MSG = (
        "Web search is not configured. Ground findings in the Customer DNA and "
        "state explicitly where external data would be needed but is unavailable."
    )

    def search(self, query: str, max_results: int = 5) -> str:
        return self._MSG

    def fetch(self, url: str) -> str:
        return self._MSG


def web_tools(backend: WebSearchTool) -> dict[str, Tool]:
    """Build the WebSearch/WebFetch Tool objects, keyed by capability name."""
    return {
        "WebSearch": Tool(
            name="web_search",
            description="Search the web for current information. Returns source-attributed results.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "max_results": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
            fn=lambda query, max_results=5: backend.search(query, max_results),
        ),
        "WebFetch": Tool(
            name="web_fetch",
            description="Fetch and return the readable text content of a URL.",
            parameters={
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
            fn=lambda url: backend.fetch(url),
        ),
    }

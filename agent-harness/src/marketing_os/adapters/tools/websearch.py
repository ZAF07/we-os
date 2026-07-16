"""Web search/fetch tool interface, a default no-op stub, and ``@tool`` adapters.

Web access is pluggable: implement :class:`WebSearchTool` (see
``websearch_playwright.py`` for the Playwright skeleton and ``websearch_tavily.py``
for the JSON-API backend) and pass it to :func:`web_tools`. Until a real backend
is wired in, :class:`NoopWebSearch` is used so ``market-research`` and
``performance-marketing`` run without crashing — they are simply told that search
is off.

The rendering helpers (:func:`_format_results`, :func:`_trim_text`) and the
shared ``NO_RESULTS_PREFIX`` live here rather than in any one backend so every
backend renders to an identical, source-attributed structure — the agent sees
the same shape regardless of which backend answered — and no backend depends on
another's module (removing one is a delete, not a rewrite).
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod

from langchain_core.tools import BaseTool, tool

_FETCH_MAX_CHARS = 8_000
_WHITESPACE = re.compile(r"[ \t\f\v]+")

NO_RESULTS_PREFIX = "No web results found"


def _shape_result(title: str, url: str, snippet: str = "") -> dict[str, str] | None:
    """Strip a raw result's fields into the shared source-attributed record shape.

    Every backend parses a different source (DuckDuckGo/Google DOM, Tavily JSON)
    but renders to one record shape, so the strip-and-skip is shared here rather
    than copied into each backend's parse.

    Args:
        title: The raw result title.
        url: The raw result URL.
        snippet: The raw result snippet, if any.

    Returns:
        A ``{title, url, snippet}`` record with each field stripped, or ``None``
        when the title or URL is empty after stripping (an unusable result the
        caller should skip).
    """
    clean_title = title.strip()
    clean_url = url.strip()
    if not clean_title or not clean_url:
        return None
    return {"title": clean_title, "url": clean_url, "snippet": snippet.strip()}


def _format_results(query: str, items: list[dict[str, str]]) -> str:
    """Render search results as a readable, source-attributed list.

    Args:
        query: The query the results are for, echoed in the header.
        items: Result records, each with ``title``, ``url``, and ``snippet`` keys.

    Returns:
        A numbered, source-attributed result list, or an explicit no-results
        message when ``items`` is empty.
    """
    if not items:
        return f'{NO_RESULTS_PREFIX} for "{query}".'
    lines = [f'Web results for "{query}":', ""]
    for index, item in enumerate(items, start=1):
        lines.append(f"{index}. {item['title']}")
        lines.append(f"   {item['url']}")
        if item.get("snippet"):
            lines.append(f"   {item['snippet']}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _trim_text(text: str, max_chars: int = _FETCH_MAX_CHARS) -> str:
    """Collapse whitespace and cap fetched page text to a readable length.

    Args:
        text: The raw page text.
        max_chars: The maximum number of characters to keep.

    Returns:
        The whitespace-normalised text, truncated with an explicit marker when it
        exceeds ``max_chars``.
    """
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = _WHITESPACE.sub(" ", raw_line).strip()
        if line == "" and (not lines or lines[-1] == ""):
            continue
        lines.append(line)
    collapsed = "\n".join(lines).strip()
    if len(collapsed) <= max_chars:
        return collapsed
    return collapsed[:max_chars].rstrip() + "\n\n[...truncated]"


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

    def close(self) -> None:
        """Release any resources the backend holds.

        The default is a no-op for stateless backends; backends that launch
        external processes (for example a browser) override this to tear them
        down.
        """
        return None


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

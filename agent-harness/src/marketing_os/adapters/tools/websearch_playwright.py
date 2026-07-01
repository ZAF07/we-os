"""Playwright-backed web search — a stub to fill in.

This is the scaffold for a browser-driven search/fetch backend. It implements the
:class:`WebSearchTool` interface so it drops straight into :func:`web_tools` once
finished::

    from marketing_os.adapters.tools.websearch_playwright import PlaywrightWebSearch
    backend = PlaywrightWebSearch()

Install the extra first::

    uv add --optional playwright playwright && uv run playwright install chromium

The methods below raise ``NotImplementedError`` on purpose. Keep them synchronous;
if you implement with Playwright's async API, drive it via ``asyncio.run(...)`` or
use ``playwright.sync_api``.
"""

from __future__ import annotations

from typing import Any

from marketing_os.adapters.tools.websearch import WebSearchTool


class PlaywrightWebSearch(WebSearchTool):
    """Browser-driven search and fetch; fill in the methods to activate."""

    def __init__(
        self,
        *,
        search_engine_url: str = "https://duckduckgo.com/html/?q={query}",
        headless: bool = True,
        timeout_ms: int = 20_000,
    ) -> None:
        """Store the backend configuration.

        Args:
            search_engine_url: The search URL template with a ``{query}`` slot.
            headless: Whether to launch the browser headless.
            timeout_ms: The per-navigation timeout in milliseconds.
        """
        self.search_engine_url = search_engine_url
        self.headless = headless
        self.timeout_ms = timeout_ms

    def _new_page(self) -> Any:
        """Launch Playwright lazily and return a new page.

        Returns:
            A Playwright page ready to navigate.

        Raises:
            NotImplementedError: Always, until implemented with ``playwright.sync_api``.
        """
        raise NotImplementedError("Implement _new_page() with playwright.sync_api.")

    def search(self, query: str, max_results: int = 5) -> str:
        """Run a search and return a readable, source-attributed result list.

        Args:
            query: The search query.
            max_results: The maximum number of results to return.

        Returns:
            A readable, source-attributed result string.

        Raises:
            NotImplementedError: Always, until implemented.
        """
        raise NotImplementedError("Implement Playwright-driven search().")

    def fetch(self, url: str) -> str:
        """Fetch a URL and return its readable text content.

        Args:
            url: The URL to fetch.

        Returns:
            The trimmed readable text of the page.

        Raises:
            NotImplementedError: Always, until implemented.
        """
        raise NotImplementedError("Implement Playwright-driven fetch().")

    def close(self) -> None:
        """Stop the browser and Playwright if they were launched eagerly."""
        return None

"""Playwright-backed web search — a browser-driven :class:`WebSearchTool`.

This backend drives a headless Chromium via ``playwright.sync_api`` to run web
searches and fetch page text. It drops straight into :func:`web_tools` and is
selected when ``MARKETING_OS_WEB=1`` (see the graph builders' ``web_backend=``
injection point)::

    from marketing_os.adapters.tools.websearch_playwright import PlaywrightWebSearch
    backend = PlaywrightWebSearch()

Install the extra first::

    uv add --optional playwright playwright && uv run playwright install chromium

Playwright is imported lazily inside :meth:`_new_page` so the module (and the
offline test suite) loads without the extra installed. The browser and Playwright
driver are launched lazily on first page and reused across calls; :meth:`close`
tears them down.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qs, quote_plus, urlparse

from marketing_os.adapters.tools.websearch import WebSearchTool

_FETCH_MAX_CHARS = 8_000
_WHITESPACE = re.compile(r"[ \t\f\v]+")


def _decode_result_href(href: str) -> str:
    """Unwrap a DuckDuckGo HTML redirect link to the real destination URL.

    DuckDuckGo's HTML endpoint wraps result links as
    ``//duckduckgo.com/l/?uddg=<url-encoded-target>&rut=...``. Direct links are
    returned unchanged.

    Args:
        href: The raw ``href`` attribute from a result anchor.

    Returns:
        The decoded destination URL, or ``href`` unchanged if it is not a
        DuckDuckGo redirect.
    """
    parsed = urlparse(href)
    if parsed.path.startswith("/l/"):
        targets = parse_qs(parsed.query).get("uddg")
        if targets:
            return targets[0]
    return href


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
        return f'No web results found for "{query}".'
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


class PlaywrightWebSearch(WebSearchTool):
    """Browser-driven search and fetch backed by a headless Chromium."""

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
        self._playwright: Any = None
        self._browser: Any = None

    def _new_page(self) -> Any:
        """Launch Playwright lazily and return a new page.

        The Playwright driver and browser are started on first use and reused
        across calls; each call returns a fresh page with the configured timeout.

        Returns:
            A Playwright page ready to navigate.
        """
        from playwright.sync_api import sync_playwright

        if self._browser is None:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=self.headless)
        page = self._browser.new_page()
        page.set_default_timeout(self.timeout_ms)
        return page

    def search(self, query: str, max_results: int = 5) -> str:
        """Run a search and return a readable, source-attributed result list.

        Args:
            query: The search query.
            max_results: The maximum number of results to return.

        Returns:
            A readable, source-attributed result string.
        """
        url = self.search_engine_url.format(query=quote_plus(query))
        page = self._new_page()
        try:
            page.goto(url, wait_until="domcontentloaded")
            items: list[dict[str, str]] = []
            for block in page.query_selector_all(".result"):
                anchor = block.query_selector("a.result__a")
                if anchor is None:
                    continue
                title = (anchor.inner_text() or "").strip()
                href = _decode_result_href(anchor.get_attribute("href") or "")
                if not title or not href:
                    continue
                snippet_el = block.query_selector(".result__snippet")
                snippet = (snippet_el.inner_text() or "").strip() if snippet_el else ""
                items.append({"title": title, "url": href, "snippet": snippet})
                if len(items) >= max_results:
                    break
            return _format_results(query, items)
        finally:
            page.close()

    def fetch(self, url: str) -> str:
        """Fetch a URL and return its readable text content.

        Args:
            url: The URL to fetch.

        Returns:
            The trimmed readable text of the page.
        """
        page = self._new_page()
        try:
            page.goto(url, wait_until="domcontentloaded")
            text = page.inner_text("body") or ""
        finally:
            page.close()
        return _trim_text(text)

    def close(self) -> None:
        """Stop the browser and Playwright driver if they were launched."""
        if self._browser is not None:
            self._browser.close()
            self._browser = None
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None

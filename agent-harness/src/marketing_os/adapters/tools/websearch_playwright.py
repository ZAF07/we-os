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

Playwright's sync API is bound to the thread that starts it, so every page
operation is routed to a single dedicated worker thread. Callers (for example
LangGraph tool executors, which use a fresh short-lived thread per tool batch)
may therefore invoke :meth:`search`, :meth:`fetch`, and :meth:`close` from any
thread.
"""

from __future__ import annotations

import re
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any, TypeVar
from urllib.parse import parse_qs, quote_plus, urlparse

from marketing_os.adapters.tools.websearch import WebSearchTool
from marketing_os.errors import ToolError

_FETCH_MAX_CHARS = 8_000
_WHITESPACE = re.compile(r"[ \t\f\v]+")

_T = TypeVar("_T")


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
        self._executor: ThreadPoolExecutor | None = None
        self._executor_lock = threading.Lock()

    def _run_on_worker(self, fn: Callable[..., _T], *args: Any) -> _T:
        """Run a callable on the backend's dedicated Playwright thread.

        The worker is a single-thread executor created lazily on first use, so
        every Playwright object lives and is used on one long-lived thread —
        the sync API raises ``greenlet.error`` when touched from any other
        thread, including the short-lived executor threads tool nodes run on.

        Args:
            fn: The callable to run on the worker thread.
            *args: Positional arguments for ``fn``.

        Returns:
            Whatever ``fn`` returns.
        """
        with self._executor_lock:
            if self._executor is None:
                self._executor = ThreadPoolExecutor(
                    max_workers=1, thread_name_prefix="playwright-web"
                )
            executor = self._executor
        return executor.submit(fn, *args).result()

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

    def _navigate(self, page: Any, url: str) -> None:
        """Navigate a page to a URL, translating browser failures to ``ToolError``.

        Navigation is the one browser step that fails on routine bad input —
        dead or hallucinated URLs, DNS misses, timeouts, TLS and HTTP-level
        aborts — which Playwright surfaces as a raw ``Error``. Wrapping it as a
        ``ToolError`` lets ``recover_tool_errors`` hand the failure back to the
        specialist as an error tool-result so it retries a different source,
        instead of the exception killing the whole run.

        Args:
            page: The Playwright page to drive.
            url: The URL to navigate to.

        Raises:
            ToolError: If Playwright fails to navigate to ``url``.
        """
        from playwright.sync_api import Error as PlaywrightError

        try:
            page.goto(url, wait_until="domcontentloaded")
        except PlaywrightError as exc:
            raise ToolError(f"Could not load {url}: {exc}") from exc

    def search(self, query: str, max_results: int = 5) -> str:
        """Run a search and return a readable, source-attributed result list.

        Safe to call from any thread; the browser work runs on the backend's
        dedicated Playwright thread.

        Args:
            query: The search query.
            max_results: The maximum number of results to return.

        Returns:
            A readable, source-attributed result string.

        Raises:
            ToolError: If the browser cannot load the search results page.
        """
        return self._run_on_worker(self._search_on_worker, query, max_results)

    def _search_on_worker(self, query: str, max_results: int) -> str:
        """Drive the browser for :meth:`search` on the Playwright thread.

        Args:
            query: The search query.
            max_results: The maximum number of results to return.

        Returns:
            A readable, source-attributed result string.
        """
        url = self.search_engine_url.format(query=quote_plus(query))
        page = self._new_page()
        try:
            self._navigate(page, url)
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

        Safe to call from any thread; the browser work runs on the backend's
        dedicated Playwright thread.

        Args:
            url: The URL to fetch.

        Returns:
            The trimmed readable text of the page.

        Raises:
            ToolError: If the browser cannot load the URL.
        """
        return self._run_on_worker(self._fetch_on_worker, url)

    def _fetch_on_worker(self, url: str) -> str:
        """Drive the browser for :meth:`fetch` on the Playwright thread.

        Args:
            url: The URL to fetch.

        Returns:
            The trimmed readable text of the page.
        """
        page = self._new_page()
        try:
            self._navigate(page, url)
            text = page.inner_text("body") or ""
        finally:
            page.close()
        return _trim_text(text)

    def close(self) -> None:
        """Stop the browser, the Playwright driver, and the worker thread.

        Safe to call from any thread and a no-op when the backend was never
        used.
        """
        with self._executor_lock:
            executor = self._executor
            self._executor = None
        if executor is None:
            return
        try:
            executor.submit(self._close_on_worker).result()
        finally:
            executor.shutdown(wait=True)

    def _close_on_worker(self) -> None:
        """Tear down the browser and driver on the Playwright thread."""
        if self._browser is not None:
            self._browser.close()
            self._browser = None
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None

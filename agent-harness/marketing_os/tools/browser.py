"""A real web-browsing tool, backed by Playwright (async API).

ADK runs tools inside an asyncio loop, so this uses Playwright's **async** API
(the sync API cannot run inside a running loop). One `WebBrowser` owns a single
Chromium browser + context for the lifetime of a campaign run and models tabs as
Playwright `Page` objects, so the agent can browse statefully: open a page, read
it, enumerate links and tabs, click links, open/switch tabs, and go back.

Each method returns a JSON-serializable dict shaped for an LLM
(`{url, title, text, links, tabs}` or `{error}`), with text and link counts
capped to keep token cost sane.

Usage (per run):

    browser = WebBrowser()
    tools = browser.as_tools()      # list of bound async methods -> ADK FunctionTools
    ...
    await browser.close()
"""

from __future__ import annotations

from typing import Any, Optional

_MAX_TEXT = 6000
_MAX_LINKS = 50
_NAV_TIMEOUT_MS = 25_000


def _normalize_url(url: str) -> str:
    """Add an https:// scheme to a bare domain, but leave real schemes intact.

    ``example.com`` -> ``https://example.com``; ``file://…`` / ``http://…`` are
    returned unchanged.
    """
    url = url.strip()
    return url if "://" in url else "https://" + url


class WebBrowser:
    """Stateful Playwright browsing session exposed to an agent as tools."""

    def __init__(self, *, headless: bool = True) -> None:
        """Create the browser holder. The browser launches lazily on first use.

        Args:
            headless: Run Chromium headless (default True; set False to watch it).
        """
        self.headless = headless
        self._pw: Any = None
        self._browser: Any = None
        self._context: Any = None
        self._active: Any = None  # the currently-focused Page

    async def _ensure(self) -> None:
        """Launch the browser/context/first page on first use (idempotent).

        Raises:
            ToolError: if Playwright or its browser binary is not installed.
        """
        if self._active is not None:
            return
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:  # pragma: no cover - env dependent
            from ..errors import ToolError

            raise ToolError(
                "Playwright is not installed. Run: uv sync && uv run playwright install chromium"
            ) from exc
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=self.headless)
        self._context = await self._browser.new_context()
        self._active = await self._context.new_page()

    # ── Snapshot helper ───────────────────────────────────────────────────────
    async def _snapshot(self) -> dict:
        """Capture the active page as a compact, LLM-friendly dict."""
        page = self._active
        try:
            text = await page.inner_text("body")
        except Exception:
            text = ""
        if len(text) > _MAX_TEXT:
            text = text[:_MAX_TEXT] + "\n…(truncated)"
        return {
            "url": page.url,
            "title": await page.title(),
            "text": text,
            "links": await self._links(),
            "tabs": [p.url for p in self._context.pages],
        }

    async def _links(self) -> list[dict]:
        """Enumerate visible links on the active page as {text, href} (absolute)."""
        out: list[dict] = []
        for el in await self._active.query_selector_all("a[href]"):
            href = await el.get_attribute("href")
            if not href:
                continue
            try:
                absolute = await self._active.evaluate(
                    "([h]) => new URL(h, window.location.href).href", [href]
                )
            except Exception:
                absolute = href
            text = (await el.inner_text() or "").strip()
            out.append({"text": text[:120], "href": absolute})
            if len(out) >= _MAX_LINKS:
                break
        return out

    # ── Agent-facing tools (each becomes an ADK FunctionTool) ─────────────────
    async def open_page(self, url: str) -> dict:
        """Open a URL in the active tab and return the page contents.

        Args:
            url: Absolute URL (include http/https).

        Returns:
            {url, title, text, links, tabs} or {error}.
        """
        await self._ensure()
        url = _normalize_url(url)
        try:
            await self._active.goto(url, wait_until="load", timeout=_NAV_TIMEOUT_MS)
        except Exception as exc:
            return {"error": f"navigation failed: {exc}", "url": url}
        return await self._snapshot()

    async def read_page(self) -> dict:
        """Re-read the currently active tab (text + links + tabs)."""
        await self._ensure()
        return await self._snapshot()

    async def get_links(self) -> dict:
        """List the links on the active tab as {links:[{text, href}]}."""
        await self._ensure()
        return {"url": self._active.url, "links": await self._links()}

    async def click_link(self, text: str) -> dict:
        """Click a link by its visible text and return the resulting page.

        If the click opens a new tab, that tab becomes active.

        Args:
            text: Visible link text (substring/exact, role-based match).
        """
        await self._ensure()
        try:
            try:
                # A click may open a popup/new tab; capture it if so.
                async with self._context.expect_page(timeout=3000) as popup:
                    await self._active.get_by_role("link", name=text).first.click(
                        timeout=_NAV_TIMEOUT_MS
                    )
                self._active = await popup.value
            except Exception:
                # No popup — a same-tab navigation; wait for it to settle.
                await self._active.wait_for_load_state("load", timeout=_NAV_TIMEOUT_MS)
        except Exception as exc:
            return {"error": f"could not click link '{text}': {exc}", "url": self._active.url}
        return await self._snapshot()

    async def open_in_new_tab(self, url: str) -> dict:
        """Open a URL in a NEW tab, make it active, and return its contents.

        Args:
            url: Absolute URL to open in a fresh tab.
        """
        await self._ensure()
        url = _normalize_url(url)
        page = await self._context.new_page()
        self._active = page
        try:
            await page.goto(url, wait_until="load", timeout=_NAV_TIMEOUT_MS)
        except Exception as exc:
            return {"error": f"navigation failed: {exc}", "url": url}
        return await self._snapshot()

    async def list_tabs(self) -> dict:
        """List all open tabs as {tabs:[{index, url, title, active}]}."""
        await self._ensure()
        tabs = []
        for i, p in enumerate(self._context.pages):
            tabs.append(
                {"index": i, "url": p.url, "title": await p.title(), "active": p is self._active}
            )
        return {"tabs": tabs}

    async def switch_tab(self, index: int) -> dict:
        """Make the tab at `index` active and return its contents.

        Args:
            index: Zero-based index into the open tabs (see list_tabs).
        """
        await self._ensure()
        pages = self._context.pages
        if index < 0 or index >= len(pages):
            return {"error": f"no tab at index {index}; {len(pages)} open."}
        self._active = pages[index]
        await self._active.bring_to_front()
        return await self._snapshot()

    async def go_back(self) -> dict:
        """Navigate the active tab back one entry in its history."""
        await self._ensure()
        try:
            await self._active.go_back(timeout=_NAV_TIMEOUT_MS)
        except Exception as exc:
            return {"error": f"cannot go back: {exc}", "url": self._active.url}
        return await self._snapshot()

    def as_tools(self) -> list:
        """Return the bound async methods to register as ADK FunctionTools.

        The names line up with the per-agent tool allowlist in agents.yaml
        (open_page, read_page, get_links, click_link, open_in_new_tab,
        list_tabs, switch_tab, go_back).
        """
        return [
            self.open_page,
            self.read_page,
            self.get_links,
            self.click_link,
            self.open_in_new_tab,
            self.list_tabs,
            self.switch_tab,
            self.go_back,
        ]

    async def close(self) -> None:
        """Tear down the browser/context/Playwright if they were launched."""
        try:
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._pw:
                await self._pw.stop()
        finally:
            self._pw = self._browser = self._context = self._active = None

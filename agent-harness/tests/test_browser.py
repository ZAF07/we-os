"""The real Playwright browser tool, driven against local file:// pages.

Verifies the required minimum: open a page, read contents, enumerate links,
click a link to navigate, open a new tab, list tabs, and switch tabs. Needs the
Chromium binary (`uv run playwright install chromium`); skipped if unavailable.
"""

from __future__ import annotations

import pytest

from marketing_os.tools.browser import WebBrowser


def _write_pages(tmp_path) -> tuple[str, str]:
    p2 = tmp_path / "page2.html"
    p1 = tmp_path / "page1.html"
    p2.write_text(
        "<html><head><title>Page Two</title></head><body><h1>Second</h1>"
        "<p>hello from two</p></body></html>",
        encoding="utf-8",
    )
    p1.write_text(
        "<html><head><title>Page One</title></head><body><h1>First</h1>"
        f'<p>intro</p><a href="file://{p2}">Go to two</a></body></html>',
        encoding="utf-8",
    )
    return f"file://{p1}", f"file://{p2}"


async def test_browser_open_click_tabs(tmp_path):
    url1, _ = _write_pages(tmp_path)
    br = WebBrowser()
    try:
        try:
            snap = await br.open_page(url1)
        except Exception as exc:  # pragma: no cover - env without chromium
            pytest.skip(f"playwright/chromium unavailable: {exc}")
        if "error" in snap:
            pytest.skip(f"could not open local page: {snap['error']}")

        assert snap["title"] == "Page One"
        assert any(l["text"] == "Go to two" for l in snap["links"])

        after = await br.click_link("Go to two")
        assert after["title"] == "Page Two"
        assert "hello from two" in after["text"]

        await br.open_in_new_tab(url1)
        tabs = await br.list_tabs()
        assert len(tabs["tabs"]) == 2
        back = await br.switch_tab(0)
        assert back["title"] == "Page Two"
    finally:
        await br.close()

"""Tests for the Playwright web backend and its gated wiring.

The browser is never launched: :meth:`PlaywrightWebSearch._new_page` is patched
to return an in-memory fake page, so search/fetch parsing is exercised without
Playwright or Chromium installed. Pure helpers are tested directly.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from marketing_os.adapters.tools import NoopWebSearch, PlaywrightWebSearch, build_tools
from marketing_os.adapters.tools.sandbox import FilesystemSandbox
from marketing_os.adapters.tools.websearch_playwright import (
    _decode_result_href,
    _format_results,
    _trim_text,
)
from marketing_os.config import Settings
from marketing_os.graph.runner import _resolve_web_backend


class _FakeElement:
    """A minimal stand-in for a Playwright element handle."""

    def __init__(
        self,
        *,
        text: str = "",
        attrs: dict[str, str] | None = None,
        children: dict[str, _FakeElement | None] | None = None,
    ) -> None:
        self._text = text
        self._attrs = attrs or {}
        self._children = children or {}

    def inner_text(self) -> str:
        return self._text

    def get_attribute(self, name: str) -> str | None:
        return self._attrs.get(name)

    def query_selector(self, selector: str) -> _FakeElement | None:
        return self._children.get(selector)


class _FakePage:
    """A minimal stand-in for a Playwright page."""

    def __init__(
        self,
        *,
        blocks: list[_FakeElement] | None = None,
        body_text: str = "",
    ) -> None:
        self._blocks = blocks or []
        self._body_text = body_text
        self.visited: list[str] = []
        self.closed = False

    def set_default_timeout(self, timeout_ms: int) -> None:
        self.timeout_ms = timeout_ms

    def goto(self, url: str, wait_until: str | None = None) -> None:
        self.visited.append(url)

    def query_selector_all(self, selector: str) -> list[_FakeElement]:
        return self._blocks if selector == ".result" else []

    def inner_text(self, selector: str) -> str:
        return self._body_text

    def close(self) -> None:
        self.closed = True


def _result_block(title: str, href: str, snippet: str) -> _FakeElement:
    """Build a fake ``.result`` block with an anchor and a snippet child."""
    return _FakeElement(
        children={
            "a.result__a": _FakeElement(text=title, attrs={"href": href}),
            ".result__snippet": _FakeElement(text=snippet),
        }
    )


def test_decode_result_href_unwraps_duckduckgo_redirect() -> None:
    href = "//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fpage&rut=abc"
    assert _decode_result_href(href) == "https://example.com/page"


def test_decode_result_href_passes_direct_links_through() -> None:
    assert _decode_result_href("https://example.com/direct") == "https://example.com/direct"


def test_format_results_numbers_and_attributes_sources() -> None:
    out = _format_results(
        "coffee", [{"title": "Beans", "url": "https://x.test", "snippet": "Fresh."}]
    )
    assert "coffee" in out
    assert "1. Beans" in out
    assert "https://x.test" in out
    assert "Fresh." in out


def test_format_results_reports_no_results() -> None:
    assert _format_results("nothing", []) == 'No web results found for "nothing".'


def test_trim_text_collapses_whitespace_and_truncates() -> None:
    assert _trim_text("a   \t  b") == "a b"
    long = "x" * (9_000)
    trimmed = _trim_text(long, max_chars=100)
    assert trimmed.endswith("[...truncated]")
    assert len(trimmed) < 200


def test_search_parses_results_and_decodes_hrefs(monkeypatch: pytest.MonkeyPatch) -> None:
    page = _FakePage(
        blocks=[
            _result_block(
                "First",
                "//duckduckgo.com/l/?uddg=https%3A%2F%2Fone.test",
                "Snippet one.",
            ),
            _result_block("Second", "https://two.test", "Snippet two."),
            _FakeElement(children={"a.result__a": None}),
        ]
    )
    backend = PlaywrightWebSearch()
    monkeypatch.setattr(backend, "_new_page", lambda: page)

    out = backend.search("green beans", max_results=5)

    assert "green+beans" in page.visited[0]
    assert "https://one.test" in out
    assert "https://two.test" in out
    assert "First" in out and "Second" in out
    assert page.closed is True


def test_search_respects_max_results(monkeypatch: pytest.MonkeyPatch) -> None:
    page = _FakePage(blocks=[_result_block(f"R{i}", f"https://r{i}.test", "s") for i in range(5)])
    backend = PlaywrightWebSearch()
    monkeypatch.setattr(backend, "_new_page", lambda: page)

    out = backend.search("q", max_results=2)

    assert "R0" in out and "R1" in out
    assert "R2" not in out


def test_fetch_returns_trimmed_body_text(monkeypatch: pytest.MonkeyPatch) -> None:
    page = _FakePage(body_text="  Hello    world  \n\n\n  again  ")
    backend = PlaywrightWebSearch()
    monkeypatch.setattr(backend, "_new_page", lambda: page)

    out = backend.fetch("https://example.com")

    assert out == "Hello world\n\nagain"
    assert page.visited == ["https://example.com"]
    assert page.closed is True


def test_search_confines_playwright_work_to_one_dedicated_thread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Calls from short-lived tool threads must all reach Playwright on one thread.

    LangGraph's ToolNode runs each tool batch on a fresh executor thread that
    exits afterwards; Playwright's sync API is bound to the thread that started
    it, so touching it from a second thread raises ``greenlet.error``. The
    backend must therefore route every page operation to a single dedicated
    worker thread, regardless of which thread invokes the tool.
    """
    page_thread_idents: list[int] = []

    def fake_new_page() -> _FakePage:
        page_thread_idents.append(threading.get_ident())
        return _FakePage(blocks=[_result_block("Hit", "https://hit.test", "s")])

    backend = PlaywrightWebSearch()
    monkeypatch.setattr(backend, "_new_page", fake_new_page)

    barrier = threading.Barrier(2)

    def search_and_report_caller_thread() -> int:
        barrier.wait()
        backend.search("q")
        return threading.get_ident()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(search_and_report_caller_thread) for _ in range(2)]
        caller_idents = [future.result() for future in futures]
    backend.close()

    assert caller_idents[0] != caller_idents[1]
    assert page_thread_idents[0] == page_thread_idents[1]
    assert page_thread_idents[0] not in caller_idents


def test_close_is_a_noop_when_backend_never_used() -> None:
    backend = PlaywrightWebSearch()
    backend.close()


def test_resolve_web_backend_gates_on_enable_web(settings: Settings) -> None:
    settings.enable_web = False
    assert _resolve_web_backend(settings, None) == (None, False)

    settings.enable_web = True
    backend, owns = _resolve_web_backend(settings, None)
    assert isinstance(backend, PlaywrightWebSearch)
    assert owns is True


def test_resolve_web_backend_does_not_own_caller_supplied(settings: Settings) -> None:
    settings.enable_web = True
    supplied = NoopWebSearch()
    assert _resolve_web_backend(settings, supplied) == (supplied, False)


def test_build_tools_uses_backend_for_web_capabilities(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    sandbox = FilesystemSandbox(settings.root, write_prefixes=["campaigns"])
    page = _FakePage(blocks=[_result_block("Hit", "https://hit.test", "why")])
    backend = PlaywrightWebSearch()
    monkeypatch.setattr(backend, "_new_page", lambda: page)

    tools = build_tools(["Read", "WebSearch", "WebFetch"], sandbox=sandbox, web_backend=backend)
    web_search = next(t for t in tools if t.name == "web_search")

    assert "https://hit.test" in web_search.invoke({"query": "beans"})


def test_build_tools_defaults_to_noop_when_no_backend(settings: Settings) -> None:
    sandbox = FilesystemSandbox(settings.root, write_prefixes=["campaigns"])
    tools = build_tools(["WebSearch"], sandbox=sandbox)
    web_search = next(t for t in tools if t.name == "web_search")

    assert "not configured" in web_search.invoke({"query": "beans"})

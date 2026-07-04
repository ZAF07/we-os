"""Tests for the Playwright web backend and its gated wiring.

The browser is never launched: :meth:`PlaywrightWebSearch._new_page` is patched
to return an in-memory fake page, so search/fetch parsing is exercised without
Playwright or Chromium installed. Pure helpers are tested directly.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

from conftest import (
    PASS_VERDICT,
    FakeReviewer,
    ProgrammableChatModel,
    deliverable_from,
    write_call,
)
from marketing_os.adapters.tools import (
    FallbackWebSearch,
    GoogleWebSearch,
    NoopWebSearch,
    PlaywrightWebSearch,
    WebSearchTool,
    build_tools,
    build_web_backend,
)
from marketing_os.adapters.tools.sandbox import FilesystemSandbox
from marketing_os.adapters.tools.websearch_playwright import (
    _decode_result_href,
    _format_results,
    _trim_text,
)
from marketing_os.config import Settings, WebBackend
from marketing_os.errors import ConfigError, ToolError
from marketing_os.graph.graph import build_single_stage_graph
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
        goto_error: Exception | None = None,
        result_selector: str = ".result",
        url: str = "https://search.test/",
    ) -> None:
        self._blocks = blocks or []
        self._body_text = body_text
        self._goto_error = goto_error
        self._result_selector = result_selector
        self.url = url
        self.visited: list[str] = []
        self.closed = False

    def set_default_timeout(self, timeout_ms: int) -> None:
        self.timeout_ms = timeout_ms

    def goto(self, url: str, wait_until: str | None = None) -> None:
        self.visited.append(url)
        if self._goto_error is not None:
            raise self._goto_error

    def query_selector_all(self, selector: str) -> list[_FakeElement]:
        return self._blocks if selector == self._result_selector else []

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


def _google_block(title: str, href: str, snippet: str) -> _FakeElement:
    """Build a fake Google ``div.g`` block with an anchor, title, and snippet."""
    return _FakeElement(
        children={
            "a": _FakeElement(attrs={"href": href}),
            "h3": _FakeElement(text=title),
            "div.VwiC3b": _FakeElement(text=snippet),
        }
    )


def _google_page(
    blocks: list[_FakeElement] | None = None,
    *,
    url: str = "https://www.google.com/search?q=x",
) -> _FakePage:
    """Build a fake page shaped like a Google results page."""
    return _FakePage(blocks=blocks, result_selector="div.g", url=url)


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


def test_fetch_wraps_navigation_failure_as_tool_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A browser navigation failure must surface as a recoverable ``ToolError``.

    LLMs regularly pick dead or hallucinated URLs; Playwright raises a raw
    ``Error`` (for example ``ERR_NAME_NOT_RESOLVED``) that must be translated at
    the backend seam so ``recover_tool_errors`` returns it to the specialist
    instead of killing the run.
    """
    from playwright.sync_api import Error as PlaywrightError

    url = "https://definitely-not-a-real-domain-x9q2.invalid/"
    page = _FakePage(goto_error=PlaywrightError("net::ERR_NAME_NOT_RESOLVED"))
    backend = PlaywrightWebSearch()
    monkeypatch.setattr(backend, "_new_page", lambda: page)

    with pytest.raises(ToolError) as excinfo:
        backend.fetch(url)

    assert url in str(excinfo.value)
    assert page.closed is True


def test_search_wraps_navigation_failure_as_tool_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A search navigation failure must surface as a recoverable ``ToolError``."""
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    page = _FakePage(goto_error=PlaywrightTimeoutError("Timeout 20000ms exceeded"))
    backend = PlaywrightWebSearch()
    monkeypatch.setattr(backend, "_new_page", lambda: page)

    with pytest.raises(ToolError):
        backend.search("green beans")

    assert page.closed is True


def test_fetch_wrapped_error_recovers_through_web_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The ``WebFetch`` tool re-raises the ``ToolError`` for the middleware to catch.

    This is the issue's repro: ``web_fetch`` on a non-resolving URL must raise
    ``ToolError`` (which ``recover_tool_errors`` converts into an error
    tool-result) rather than a raw Playwright error that is fatal to the run.
    """
    from playwright.sync_api import Error as PlaywrightError

    from marketing_os.adapters.tools.websearch import web_tools

    url = "https://definitely-not-a-real-domain-x9q2.invalid/"
    page = _FakePage(goto_error=PlaywrightError("net::ERR_NAME_NOT_RESOLVED"))
    backend = PlaywrightWebSearch()
    monkeypatch.setattr(backend, "_new_page", lambda: page)

    web_fetch = web_tools(backend)["WebFetch"]

    with pytest.raises(ToolError):
        web_fetch.invoke({"url": url})


def test_navigation_failure_recovers_into_error_tool_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A wrapped navigation failure comes back as an error ``ToolMessage``.

    This closes the chain the issue cares about: the ``ToolError`` the backend
    raises must be turned into a recoverable error tool-result by
    ``recover_tool_errors`` so the specialist retries a different source and the
    graph run continues, instead of the exception escaping the tool node.
    """
    from langchain.agents.middleware import ToolCallRequest
    from playwright.sync_api import Error as PlaywrightError

    from marketing_os.adapters.tools.websearch import web_tools
    from marketing_os.agents.middleware import recover_tool_errors

    url = "https://definitely-not-a-real-domain-x9q2.invalid/"
    page = _FakePage(goto_error=PlaywrightError("net::ERR_NAME_NOT_RESOLVED"))
    backend = PlaywrightWebSearch()
    monkeypatch.setattr(backend, "_new_page", lambda: page)
    web_fetch = web_tools(backend)["WebFetch"]

    request = ToolCallRequest(
        tool_call={"id": "call-1", "name": "web_fetch", "args": {"url": url}},
        tool=web_fetch,
        state={},
        runtime=None,
    )

    result = recover_tool_errors.wrap_tool_call(
        request, lambda req: web_fetch.invoke(req.tool_call["args"])
    )

    assert result.status == "error"
    assert url in result.content
    assert result.tool_call_id == "call-1"


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
    assert isinstance(backend, FallbackWebSearch)
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


async def test_sync_web_tool_runs_under_async_specialist_node(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A sync Playwright web tool still works when driven by an async node.

    Closes ADR-0009's AC2 end to end: the specialist node is now ``async`` while
    the web backend stays the thread-confined sync Playwright backend (ADR-0007).
    LangGraph dispatches the sync tool to a worker thread while the node awaits on
    the event loop, so the tool must run off the main thread and the stage must
    complete normally.
    """
    page_thread_idents: list[int] = []

    def fake_new_page() -> _FakePage:
        page_thread_idents.append(threading.get_ident())
        return _FakePage(blocks=[_result_block("Hit", "https://hit.test", "why")])

    backend = PlaywrightWebSearch()
    monkeypatch.setattr(backend, "_new_page", fake_new_page)

    def handler(messages: list[BaseMessage], index: int) -> AIMessage:
        last = messages[-1]
        if isinstance(last, ToolMessage):
            if "hit.test" in str(last.content):
                return write_call(deliverable_from(messages), "# Deliverable\n\nFrom the web.")
            return AIMessage(content="Saved. Done.")
        return AIMessage(
            content="",
            tool_calls=[{"name": "web_search", "args": {"query": "beans"}, "id": "c1"}],
        )

    graph = build_single_stage_graph(
        settings,
        "research",
        model=ProgrammableChatModel(handler=handler),
        reviewer=FakeReviewer([PASS_VERDICT]),
        web_backend=backend,
    )
    state = await graph.ainvoke(
        {"customer": "acme", "slug": "acme"},
        config={"configurable": {"thread_id": "web-async"}, "recursion_limit": 50},
    )
    backend.close()

    assert state["error"] is None
    assert (settings.campaigns_dir / "acme" / "research.md").is_file()
    assert page_thread_idents, "the web backend was never invoked under the async node"
    assert threading.get_ident() not in page_thread_idents


def test_build_tools_defaults_to_noop_when_no_backend(settings: Settings) -> None:
    sandbox = FilesystemSandbox(settings.root, write_prefixes=["campaigns"])
    tools = build_tools(["WebSearch"], sandbox=sandbox)
    web_search = next(t for t in tools if t.name == "web_search")

    assert "not configured" in web_search.invoke({"query": "beans"})


# --- Google backend ---------------------------------------------------------


def test_google_search_hits_google_and_parses_results(monkeypatch: pytest.MonkeyPatch) -> None:
    page = _google_page(
        [
            _google_block("First", "https://one.test", "Snippet one."),
            _google_block("Second", "https://two.test", "Snippet two."),
        ]
    )
    backend = GoogleWebSearch()
    monkeypatch.setattr(backend, "_new_page", lambda: page)

    out = backend.search("green beans", max_results=5)

    assert "google.com/search" in page.visited[0]
    assert "green+beans" in page.visited[0]
    assert "https://one.test" in out and "https://two.test" in out
    assert "First" in out and "Second" in out
    assert page.closed is True


def test_google_search_respects_max_results(monkeypatch: pytest.MonkeyPatch) -> None:
    page = _google_page([_google_block(f"R{i}", f"https://r{i}.test", "s") for i in range(5)])
    backend = GoogleWebSearch()
    monkeypatch.setattr(backend, "_new_page", lambda: page)

    out = backend.search("q", max_results=2)

    assert "R0" in out and "R1" in out
    assert "R2" not in out


def test_google_search_raises_tool_error_on_consent_wall(monkeypatch: pytest.MonkeyPatch) -> None:
    """A consent-wall redirect must surface as a recoverable ``ToolError``."""
    page = _google_page([], url="https://consent.google.com/m?continue=...")
    backend = GoogleWebSearch()
    monkeypatch.setattr(backend, "_new_page", lambda: page)

    with pytest.raises(ToolError):
        backend.search("beans")
    assert page.closed is True


def test_google_search_raises_tool_error_on_captcha(monkeypatch: pytest.MonkeyPatch) -> None:
    """A bot-detection ``/sorry/`` redirect must surface as a recoverable ``ToolError``."""
    page = _google_page(
        [_google_block("X", "https://x.test", "s")],
        url="https://www.google.com/sorry/index?continue=...",
    )
    backend = GoogleWebSearch()
    monkeypatch.setattr(backend, "_new_page", lambda: page)

    with pytest.raises(ToolError):
        backend.search("beans")


def test_google_search_raises_tool_error_on_zero_parse(monkeypatch: pytest.MonkeyPatch) -> None:
    """Markup that yields no parseable results is recoverable, not a friendly empty."""
    page = _google_page([])
    backend = GoogleWebSearch()
    monkeypatch.setattr(backend, "_new_page", lambda: page)

    with pytest.raises(ToolError):
        backend.search("beans")


def test_google_fetch_reuses_playwright_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """``fetch`` is inherited from the Playwright base — no Google-specific logic."""
    page = _FakePage(body_text="  Hello   world  ")
    backend = GoogleWebSearch()
    monkeypatch.setattr(backend, "_new_page", lambda: page)

    assert backend.fetch("https://example.com") == "Hello world"
    assert page.visited == ["https://example.com"]


# --- Fallback chain ---------------------------------------------------------


class _StubBackend(WebSearchTool):
    """A scripted backend that returns a string, raises, or reports empty."""

    def __init__(self, *, result: str | None = None, error: Exception | None = None) -> None:
        self._result = result
        self._error = error
        self.searched = False
        self.closed = False

    def search(self, query: str, max_results: int = 5) -> str:
        self.searched = True
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result

    def fetch(self, url: str) -> str:
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result

    def close(self) -> None:
        self.closed = True


def test_fallback_returns_first_successful_backend() -> None:
    first = _StubBackend(result="hit from first")
    second = _StubBackend(result="hit from second")
    chain = FallbackWebSearch([first, second])

    assert chain.search("q") == "hit from first"
    assert second.searched is False


def test_fallback_falls_through_on_tool_error() -> None:
    first = _StubBackend(error=ToolError("google blocked"))
    second = _StubBackend(result="hit from second")
    chain = FallbackWebSearch([first, second])

    assert chain.search("q") == "hit from second"
    assert first.searched is True and second.searched is True


def test_fallback_falls_through_on_empty_result() -> None:
    first = _StubBackend(result='No web results found for "q".')
    second = _StubBackend(result="hit from second")
    chain = FallbackWebSearch([first, second])

    assert chain.search("q") == "hit from second"


def test_fallback_single_backend_returns_empty_as_today() -> None:
    """A single configured backend behaves exactly as today: empty is not an error."""
    only = _StubBackend(result='No web results found for "q".')
    chain = FallbackWebSearch([only])

    assert chain.search("q") == 'No web results found for "q".'


def test_fallback_reraises_last_backend_tool_error() -> None:
    first = _StubBackend(error=ToolError("first down"))
    second = _StubBackend(error=ToolError("second down"))
    chain = FallbackWebSearch([first, second])

    with pytest.raises(ToolError):
        chain.search("q")


def test_fallback_close_cascades_to_all_backends() -> None:
    first = _StubBackend(result="a")
    second = _StubBackend(result="b")
    FallbackWebSearch([first, second]).close()

    assert first.closed is True and second.closed is True


def test_fallback_fetch_delegates_and_falls_through() -> None:
    first = _StubBackend(error=ToolError("cannot fetch"))
    second = _StubBackend(result="page text")
    chain = FallbackWebSearch([first, second])

    assert chain.fetch("https://x.test") == "page text"


# --- Backend registry + config-driven resolution ----------------------------


def test_build_web_backend_composes_named_chain() -> None:
    chain = build_web_backend([WebBackend.GOOGLE, WebBackend.DUCKDUCKGO])
    assert isinstance(chain, FallbackWebSearch)
    assert isinstance(chain.backends[0], GoogleWebSearch)
    assert isinstance(chain.backends[1], PlaywrightWebSearch)


def test_build_web_backend_rejects_empty_chain() -> None:
    with pytest.raises(ConfigError):
        build_web_backend([])


def test_resolve_web_backend_builds_configured_chain(settings: Settings) -> None:
    settings.enable_web = True
    settings.web_backends = [WebBackend.GOOGLE, WebBackend.DUCKDUCKGO]
    backend, owns = _resolve_web_backend(settings, None)

    assert isinstance(backend, FallbackWebSearch)
    assert isinstance(backend.backends[0], GoogleWebSearch)
    assert owns is True


def test_settings_parse_web_backends_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MARKETING_OS_WEB_BACKENDS", "duckduckgo, google , noop")
    assert Settings().web_backends == [
        WebBackend.DUCKDUCKGO,
        WebBackend.GOOGLE,
        WebBackend.NOOP,
    ]


def test_settings_defaults_web_backends_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MARKETING_OS_WEB_BACKENDS", raising=False)
    assert Settings().web_backends == [WebBackend.GOOGLE, WebBackend.DUCKDUCKGO]


def test_settings_rejects_unknown_web_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MARKETING_OS_WEB_BACKENDS", "google,bing")
    with pytest.raises(ConfigError):
        Settings()

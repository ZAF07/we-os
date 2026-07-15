"""Offline tests for the Tavily web backend.

The HTTP layer is faked with :class:`httpx.MockTransport`, so a real
:class:`httpx.Client` drives the adapter (status handling, JSON decoding, error
types are exercised) without any network access. A handler inspects each request
and returns a canned response — or raises a transport error — so every branch of
the failure map is covered deterministically.
"""

from __future__ import annotations

import json
from collections.abc import Callable

import httpx
import pytest

from marketing_os.adapters.tools.websearch_tavily import TavilyWebSearch
from marketing_os.errors import ConfigError, ToolError

_Handler = Callable[[httpx.Request], httpx.Response]


def _backend(handler: _Handler, *, search_depth: str = "basic") -> TavilyWebSearch:
    """Build a Tavily backend whose HTTP client is a faked transport."""
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return TavilyWebSearch("tvly-test-key", search_depth=search_depth, client=client)


def _search_results(count: int) -> list[dict[str, object]]:
    """Build ``count`` Tavily search records with ascending scores.

    Record ``i`` has ``score == i``, so ranking by score descending reverses the
    natural order — a clean signal that the adapter ranks rather than passes
    Tavily's order through.
    """
    return [
        {
            "title": f"R{index:02d}",
            "url": f"https://r{index:02d}.test",
            "content": f"snippet {index:02d}",
            "score": float(index),
        }
        for index in range(count)
    ]


def test_search_sends_overfetch_payload_and_bearer_key() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("Authorization")
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"results": _search_results(3)})

    _backend(handler, search_depth="advanced").search("beans", max_results=5)

    assert captured["url"] == "https://api.tavily.com/search"
    assert captured["auth"] == "Bearer tvly-test-key"
    body = captured["body"]
    assert body["query"] == "beans"
    assert body["max_results"] == 20
    assert body["search_depth"] == "advanced"
    assert body["include_answer"] is False


def test_search_ranks_by_score_and_respects_max_results() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": _search_results(20)})

    out = _backend(handler).search("q", max_results=5)

    lines = [line for line in out.splitlines() if line.strip().startswith(tuple("12345"))]
    ordered_titles = [line.split(". ", 1)[1] for line in lines if ". " in line]
    assert ordered_titles == ["R19", "R18", "R17", "R16", "R15"]
    assert "R14" not in out


def test_search_caps_working_set_at_ten() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": _search_results(20)})

    out = _backend(handler).search("q", max_results=100)

    for kept in range(10, 20):
        assert f"R{kept:02d}" in out
    assert "R09" not in out


def test_search_never_prints_score() -> None:
    results = [
        {
            "title": "Beans",
            "url": "https://x.test",
            "content": "Fresh.",
            "score": 0.876543,
        }
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": results})

    out = _backend(handler).search("coffee")

    assert "Beans" in out and "https://x.test" in out and "Fresh." in out
    assert "0.876543" not in out
    assert "score" not in out.lower()


def test_search_empty_results_returns_no_results_message() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": []})

    out = _backend(handler).search("nothing")

    assert out == 'No web results found for "nothing".'


def test_fetch_extracts_readable_text() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"results": [{"url": "https://x.test", "raw_content": "  Hello   world  "}]},
        )

    out = _backend(handler, search_depth="advanced").fetch("https://x.test")

    assert out == "Hello world"
    assert captured["url"] == "https://api.tavily.com/extract"
    body = captured["body"]
    assert body["urls"] == "https://x.test"
    assert body["extract_depth"] == "advanced"


def test_fetch_empty_results_raises_tool_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": [], "failed_results": ["https://x.test"]})

    with pytest.raises(ToolError):
        _backend(handler).fetch("https://x.test")


@pytest.mark.parametrize("status", [429, 432, 433, 500, 502, 503])
def test_recoverable_status_raises_tool_error(status: int) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"detail": "nope"})

    with pytest.raises(ToolError):
        _backend(handler).search("q")


@pytest.mark.parametrize("status", [401, 403])
def test_invalid_key_status_raises_config_error(status: int) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"detail": "bad key"})

    with pytest.raises(ConfigError):
        _backend(handler).search("q")


def test_network_error_raises_tool_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    with pytest.raises(ToolError):
        _backend(handler).search("q")


def test_timeout_raises_tool_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("read timed out")

    with pytest.raises(ToolError):
        _backend(handler).fetch("https://x.test")


def test_empty_api_key_is_rejected_at_construction() -> None:
    with pytest.raises(ConfigError):
        TavilyWebSearch("")


def test_close_closes_owned_client() -> None:
    backend = TavilyWebSearch("tvly-test-key")
    backend.close()

    assert backend._client.is_closed is True


def test_close_leaves_injected_client_open() -> None:
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200)))
    backend = TavilyWebSearch("tvly-test-key", client=client)

    backend.close()

    assert client.is_closed is False

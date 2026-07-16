"""Tavily-backed web search — a JSON-API :class:`WebSearchTool`.

Tavily (https://tavily.com) is a retrieval API built for LLM agents: ``/search``
returns ranked, source-attributed results and ``/extract`` returns clean page
text, both as JSON over plain HTTP with no browser. This backend drops straight
into :func:`web_tools` and the :class:`FallbackWebSearch` chain, so it is a
drop-in alternative to the Playwright backends.

The HTTP client is an injected :class:`httpx.Client`, so the whole adapter is
exercised offline against a faked transport — there are no live API calls in the
default test suite. The failure map (HTTP status / network / timeout →
recoverable :class:`ToolError`; empty results → the shared no-results string;
invalid key → terminal :class:`ConfigError`) is applied at the single
:meth:`_post` seam so both operations degrade identically.
"""

from __future__ import annotations

from typing import Any

import httpx

from marketing_os.adapters.tools.websearch import (
    WebSearchTool,
    _format_results,
    _shape_result,
    _trim_text,
)
from marketing_os.errors import ConfigError, ToolError

_TAVILY_BASE_URL = "https://api.tavily.com"
_SEARCH_ENDPOINT = "/search"
_EXTRACT_ENDPOINT = "/extract"
_DEFAULT_TIMEOUT = 30.0

_OVERFETCH = 20
_WORKING_SET = 10

_INVALID_KEY_STATUS = frozenset({401, 403})


class TavilyWebSearch(WebSearchTool):
    """Tavily ``/search`` + ``/extract`` retrieval over an injected HTTP client.

    ``search`` over-fetches Tavily's maximum in one credit-flat request, ranks the
    results by Tavily's relevance ``score``, and renders the top slice in the
    shared source-attributed format; ``score`` drives selection only and is never
    printed. ``fetch`` returns clean page text via ``/extract``. Both endpoints
    share :meth:`_post`, so quota/transient failures degrade to a recoverable
    :class:`ToolError` (the fallback chain advances) while an invalid key raises a
    terminal :class:`ConfigError` that stops the run rather than silently burning
    a campaign on the fallback engine.
    """

    def __init__(
        self,
        api_key: str,
        *,
        search_depth: str = "basic",
        client: httpx.Client | None = None,
        base_url: str = _TAVILY_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        """Store the Tavily configuration and HTTP client.

        Args:
            api_key: The Tavily API key, sent as a bearer token.
            search_depth: Tavily depth (``basic`` | ``advanced``) driving both
                ``search_depth`` and ``extract_depth``.
            client: An injected :class:`httpx.Client`; when ``None`` a client
                owned by this backend is created and closed in :meth:`close`.
            base_url: The Tavily API base URL.
            timeout: The per-request timeout in seconds for an owned client.

        Raises:
            ConfigError: If ``api_key`` is empty; a Tavily backend with no key is
                meaningless and should be skipped by the builder, not constructed.
        """
        if not api_key:
            raise ConfigError("TavilyWebSearch requires a non-empty API key.")
        self._api_key = api_key
        self._search_depth = search_depth
        self._base_url = base_url.rstrip("/")
        self._owns_client = client is None
        self._client = client if client is not None else httpx.Client(timeout=timeout)

    @classmethod
    def from_settings(
        cls, api_key: str | None, *, search_depth: str = "basic"
    ) -> TavilyWebSearch | None:
        """Build a Tavily backend from settings, or ``None`` when no key is set.

        The "no key → skip this backend" decision lives here rather than at the
        chain builder, so the single fact "Tavily needs a key" is owned by the
        Tavily backend. The builder skips (and warns) when this returns ``None``.

        Args:
            api_key: The Tavily API key, or ``None``/empty when unconfigured.
            search_depth: The Tavily depth to construct the backend with.

        Returns:
            A configured :class:`TavilyWebSearch`, or ``None`` when no key is set.
        """
        if not api_key:
            return None
        return cls(api_key, search_depth=search_depth)

    def search(self, query: str, max_results: int = 5) -> str:
        """Search Tavily and return the top results in the shared format.

        Over-fetches up to Tavily's maximum (20) in one flat-rate request, ranks
        by ``score`` descending, keeps the top 10 as the working set, and renders
        the first ``min(max_results, 10)`` as a source-attributed list.

        Args:
            query: The search query.
            max_results: The maximum number of results to return.

        Returns:
            A readable, source-attributed result list, or the shared no-results
            message when Tavily returned nothing.

        Raises:
            ToolError: If the request fails recoverably (quota, 5xx, network,
                timeout).
            ConfigError: If Tavily rejects the API key.
        """
        payload = {
            "query": query,
            "max_results": _OVERFETCH,
            "search_depth": self._search_depth,
            "include_answer": False,
        }
        data = self._post(_SEARCH_ENDPOINT, payload)
        results = data.get("results") or []
        if not results:
            return _format_results(query, [])
        ranked = sorted(results, key=lambda result: result.get("score") or 0.0, reverse=True)
        working_set = ranked[:_WORKING_SET]
        limit = min(max_results, _WORKING_SET)
        items = [
            record
            for result in working_set[:limit]
            if (
                record := _shape_result(
                    result.get("title") or "",
                    result.get("url") or "",
                    result.get("content") or "",
                )
            )
            is not None
        ]
        return _format_results(query, items)

    def fetch(self, url: str) -> str:
        """Fetch a URL's readable text via Tavily ``/extract``.

        Args:
            url: The URL to extract.

        Returns:
            The trimmed readable text of the page.

        Raises:
            ToolError: If extraction fails recoverably or Tavily returned no
                content for the URL.
            ConfigError: If Tavily rejects the API key.
        """
        payload = {"urls": url, "extract_depth": self._search_depth}
        data = self._post(_EXTRACT_ENDPOINT, payload)
        results = data.get("results") or []
        if not results:
            raise ToolError(f"Tavily could not extract content from {url}.")
        raw_content = results[0].get("raw_content") or ""
        return _trim_text(raw_content)

    def _post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST a JSON payload to a Tavily endpoint and apply the failure map.

        Args:
            endpoint: The Tavily endpoint path (``/search`` or ``/extract``).
            payload: The JSON request body.

        Returns:
            The decoded JSON response body.

        Raises:
            ToolError: On a recoverable failure — quota (429/432/433), any 5xx,
                any other non-2xx status, a network/transport error, a timeout, or
                an unparseable body — so the fallback chain advances.
            ConfigError: On 401/403, a present-but-rejected key, so the run stops
                loudly instead of silently falling through to scraping.
        """
        url = f"{self._base_url}{endpoint}"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        try:
            response = self._client.post(url, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise ToolError(f"Tavily request to {endpoint} timed out: {exc}") from exc
        except httpx.HTTPError as exc:
            raise ToolError(f"Tavily request to {endpoint} failed: {exc}") from exc

        status = response.status_code
        if status in _INVALID_KEY_STATUS:
            raise ConfigError(
                f"Tavily rejected the API key (HTTP {status}). Check MARKETING_OS_TAVILY_API_KEY."
            )
        if not response.is_success:
            raise ToolError(f"Tavily {endpoint} returned HTTP {status} (recoverable).")
        try:
            body: dict[str, Any] = response.json()
        except ValueError as exc:
            raise ToolError(f"Tavily {endpoint} returned an unparseable body: {exc}") from exc
        return body

    def close(self) -> None:
        """Close the HTTP client when this backend owns it."""
        if self._owns_client:
            self._client.close()

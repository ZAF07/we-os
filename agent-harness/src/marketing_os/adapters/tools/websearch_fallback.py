"""Priority-ordered fallback across web backends, and the backend registry.

A :class:`FallbackWebSearch` composes several :class:`WebSearchTool` backends
into one that still *is* a :class:`WebSearchTool`, so the graph wiring is
untouched. ``search`` tries each backend in order and falls through to the next
on a recoverable :class:`ToolError` or an empty result set; the last backend's
result — friendly "no results" string or raised ``ToolError`` — surfaces as-is,
so a single configured backend behaves exactly as it did before this seam
existed. :func:`build_web_backend` turns the config's ordered list of backend
identifiers (``google`` / ``duckduckgo`` / ``noop``) into that chain.
"""

from __future__ import annotations

from collections.abc import Callable

from marketing_os.adapters.tools.websearch import NoopWebSearch, WebSearchTool
from marketing_os.adapters.tools.websearch_playwright import (
    NO_RESULTS_PREFIX,
    GoogleWebSearch,
    PlaywrightWebSearch,
)
from marketing_os.config import WebBackend
from marketing_os.errors import ConfigError, ToolError


def _is_empty_result(text: str) -> bool:
    """Report whether a formatted search result carries no findings.

    Args:
        text: A result string produced by a backend's ``search``.

    Returns:
        ``True`` when the string is the shared "no results" message, meaning the
        chain should fall through to the next backend.
    """
    return text.startswith(NO_RESULTS_PREFIX)


class FallbackWebSearch(WebSearchTool):
    """A :class:`WebSearchTool` that tries several backends in priority order."""

    def __init__(self, backends: list[WebSearchTool]) -> None:
        """Store the ordered backends the chain delegates to.

        Args:
            backends: The backends to try, in priority order; the first is
                preferred and later ones are fallbacks.

        Raises:
            ConfigError: If ``backends`` is empty.
        """
        if not backends:
            raise ConfigError("A web backend chain needs at least one backend.")
        self.backends = backends

    def _run_chain(
        self,
        operation: Callable[[WebSearchTool], str],
        *,
        is_acceptable: Callable[[str], bool],
        description: str,
    ) -> str:
        """Run an operation across the backends, falling through until one succeeds.

        Each backend is tried in priority order. A recoverable :class:`ToolError`
        or an unacceptable result from a non-final backend advances to the next;
        the final backend's outcome (result or raised error) surfaces unchanged,
        so a single-backend chain behaves exactly as that backend alone.

        Args:
            operation: The call to make against each backend (``search``/``fetch``).
            is_acceptable: Predicate deciding whether a returned result ends the
                walk; when it is ``False`` for a non-final backend, the chain
                falls through.
            description: A short phrase naming the operation, for the error raised
                when no backend is available.

        Returns:
            The first acceptable result, or the final backend's result.

        Raises:
            ToolError: If the final backend fails recoverably.
        """
        last_index = len(self.backends) - 1
        for index, backend in enumerate(self.backends):
            is_last = index == last_index
            try:
                result = operation(backend)
            except ToolError:
                if is_last:
                    raise
                continue
            if is_last or is_acceptable(result):
                return result
        raise ToolError(f"No web backend could {description}.")

    def search(self, query: str, max_results: int = 5) -> str:
        """Search each backend in order until one returns findings.

        A recoverable :class:`ToolError` or an empty result set from a non-final
        backend advances to the next; the final backend's outcome (result or
        raised error) is returned or propagated unchanged.

        Args:
            query: The search query.
            max_results: The maximum number of results to return.

        Returns:
            The first non-empty, source-attributed result list.

        Raises:
            ToolError: If the final backend fails recoverably.
        """
        return self._run_chain(
            lambda backend: backend.search(query, max_results),
            is_acceptable=lambda result: not _is_empty_result(result),
            description=f"search for '{query}'",
        )

    def fetch(self, url: str) -> str:
        """Fetch a URL via the first backend that succeeds.

        Args:
            url: The URL to fetch.

        Returns:
            The readable text content of the page.

        Raises:
            ToolError: If the final backend cannot fetch the URL.
        """
        return self._run_chain(
            lambda backend: backend.fetch(url),
            is_acceptable=lambda _result: True,
            description=f"fetch '{url}'",
        )

    def close(self) -> None:
        """Release every backend the chain owns."""
        for backend in self.backends:
            backend.close()


_BACKEND_FACTORIES: dict[WebBackend, Callable[[], WebSearchTool]] = {
    WebBackend.GOOGLE: GoogleWebSearch,
    WebBackend.DUCKDUCKGO: PlaywrightWebSearch,
    WebBackend.NOOP: NoopWebSearch,
}


def build_web_backend(identifiers: list[WebBackend]) -> FallbackWebSearch:
    """Build a fallback chain from an ordered list of backends.

    The identifiers are already validated (they are :class:`WebBackend` members,
    parsed at config load); this only guards against an enum member that has no
    registered factory, i.e. internal registry drift.

    Args:
        identifiers: Backends in priority order.

    Returns:
        A :class:`FallbackWebSearch` wrapping the named backends in order.

    Raises:
        ConfigError: If ``identifiers`` is empty or names a backend with no
            registered factory.
    """
    if not identifiers:
        known = ", ".join(member.value for member in WebBackend)
        raise ConfigError(f"No web backends configured. Set MARKETING_OS_WEB_BACKENDS to: {known}.")
    backends: list[WebSearchTool] = []
    for identifier in identifiers:
        factory = _BACKEND_FACTORIES.get(identifier)
        if factory is None:
            raise ConfigError(f"No factory registered for web backend '{identifier}'.")
        backends.append(factory())
    return FallbackWebSearch(backends)

"""Filesystem tools — LangChain ``@tool`` adapters for the specialists' file I/O.

Each factory returns tools keyed by the Claude-style capability name declared in
an agent's frontmatter (``Read``, ``Glob``, ``Grep``, ``Write``).

Reads are split by what is being read. Code-shipped material — governance,
templates, knowledge, guardrails — resolves through the :class:`FilesystemSandbox`.
Tenant-owned documents (the Brand DNA and campaign deliverables) resolve through
the tenant-scoped :class:`~marketing_os.ports.DocumentStore` using the tenant
injected from graph state, so a specialist reads only its own business's
documents no matter what path its prompt asks for (ADR-0013). Writes are
scope-checked by :func:`validate_campaign_write` and likewise stored through the
port. A violation raises :class:`ToolError`, which the agent's tool node converts
into a recoverable error message rather than crashing the run.
"""

from __future__ import annotations

from typing import Annotated

from langchain_core.tools import BaseTool, tool
from langgraph.prebuilt import InjectedState

from marketing_os.adapters.tools.sandbox import FilesystemSandbox
from marketing_os.adapters.tools.scope import validate_campaign_write
from marketing_os.errors import DocumentNotFoundError, ToolError
from marketing_os.ports import DocumentStore

_DNA_DOCUMENT = "dna.md"
_CAMPAIGNS_ROOT = "campaigns"


def document_path(path: str) -> str:
    """Normalise a path a specialist asked for into a logical document path.

    Args:
        path: The path as the model wrote it, possibly with ``./`` prefixes.

    Returns:
        The path with surrounding whitespace and leading ``./`` segments removed.
    """
    normalised = path.strip()
    while normalised.startswith("./"):
        normalised = normalised[2:]
    return normalised


def is_tenant_document(path: str) -> bool:
    """Return whether a logical path names a tenant-owned document.

    Args:
        path: The path a specialist asked to read.

    Returns:
        ``True`` for the Brand DNA and anything under ``campaigns/``, which only
        the tenant-scoped document store may serve.
    """
    normalised = document_path(path)
    return normalised == _DNA_DOCUMENT or normalised.startswith(f"{_CAMPAIGNS_ROOT}/")


def filesystem_tools(
    sandbox: FilesystemSandbox,
    *,
    document_store: DocumentStore,
    include_write: bool,
) -> dict[str, BaseTool]:
    """Build filesystem tools keyed by Claude-style capability name.

    Args:
        sandbox: The sandbox that resolves and guards every read path.
        document_store: The store deliverable writes resolve through.
        include_write: Whether to include the write tool (granted only to agents
            that declare the ``Write`` capability).

    Returns:
        A mapping of capability name to the corresponding LangChain tool.
    """

    @tool(parse_docstring=True)
    def read_file(path: str, tenant: Annotated[str, InjectedState("tenant")]) -> str:
        """Read a UTF-8 text file — a repository document, or one of this campaign's.

        Args:
            path: The Brand DNA (``dna.md``), a campaign document under
                ``campaigns/<slug>/``, or a repository file such as a knowledge
                or guardrail document.
            tenant: The tenant this run belongs to, injected from graph state and
                hidden from the model; scopes every tenant-document read.

        Returns:
            The file contents as text.

        Raises:
            ToolError: If a tenant document does not exist for this tenant.
        """
        if not is_tenant_document(path):
            return sandbox.read(path)
        try:
            return document_store.read(tenant, document_path(path))
        except DocumentNotFoundError as exc:
            raise ToolError(f"File not found: {path}") from exc

    @tool(parse_docstring=True)
    def glob(pattern: str) -> str:
        """List files matching a glob pattern, relative to the repository root.

        Args:
            pattern: A glob pattern such as ``knowledge/**/*.md``.

        Returns:
            Newline-separated matching paths.
        """
        return sandbox.glob(pattern)

    @tool(parse_docstring=True)
    def grep(pattern: str, path: str | None = None) -> str:
        """Search repository markdown for a regex and return ``file:line`` matches.

        Args:
            pattern: The regular expression to search for.
            path: Optional file or directory to narrow the search to.

        Returns:
            Newline-separated ``path:line: text`` matches.
        """
        return sandbox.grep(pattern, path)

    @tool(parse_docstring=True)
    def write_file(
        path: str,
        content: str,
        slug: Annotated[str, InjectedState("slug")],
        tenant: Annotated[str, InjectedState("tenant")],
    ) -> str:
        """Write a UTF-8 text file under ``campaigns/`` to save a deliverable.

        Args:
            path: Path under ``campaigns/<slug>/``, relative to the repository root.
            content: The full text to write.
            slug: The live run slug, injected from graph state and hidden from the
                model; scopes the write to ``campaigns/<slug>/``.
            tenant: The tenant the run belongs to, injected from graph state and
                hidden from the model; scopes the write in the document store.

        Returns:
            A short confirmation message.
        """
        document = validate_campaign_write(path, slug)
        document_store.write(tenant, document, content)
        return f"Wrote {len(content)} chars to {path}"

    tools: dict[str, BaseTool] = {"Read": read_file, "Glob": glob, "Grep": grep}
    if include_write:
        tools["Write"] = write_file
    return tools

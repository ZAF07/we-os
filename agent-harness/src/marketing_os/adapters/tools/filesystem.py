"""Filesystem tools — LangChain ``@tool`` adapters for the specialists' file I/O.

Each factory returns tools keyed by the Claude-style capability name declared in
an agent's frontmatter (``Read``, ``Glob``, ``Grep``, ``Write``). Reads resolve
through the :class:`FilesystemSandbox` (repo-wide, read-only); writes are
scope-checked by :func:`validate_campaign_write` and stored through the
:class:`~marketing_os.ports.DocumentStore` port, so where a deliverable lives is
pluggable. A violation raises :class:`ToolError`, which the agent's tool node
converts into a recoverable error message rather than crashing the run.
"""

from __future__ import annotations

from typing import Annotated

from langchain_core.tools import BaseTool, tool
from langgraph.prebuilt import InjectedState

from marketing_os.adapters.tools.sandbox import FilesystemSandbox
from marketing_os.adapters.tools.scope import validate_campaign_write
from marketing_os.ports import DocumentStore


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
    def read_file(path: str) -> str:
        """Read a UTF-8 text file from the repository.

        Args:
            path: Path to the file, relative to the repository root.

        Returns:
            The file contents as text.
        """
        return sandbox.read(path)

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
        customer: Annotated[str, InjectedState("customer")],
    ) -> str:
        """Write a UTF-8 text file under ``campaigns/`` to save a deliverable.

        Args:
            path: Path under ``campaigns/<slug>/``, relative to the repository root.
            content: The full text to write.
            slug: The live run slug, injected from graph state and hidden from the
                model; scopes the write to ``campaigns/<slug>/``.
            customer: The tenant the run belongs to, injected from graph state and
                hidden from the model; scopes the write in the document store.

        Returns:
            A short confirmation message.
        """
        document = validate_campaign_write(path, slug)
        document_store.write(customer, document, content)
        return f"Wrote {len(content)} chars to {path}"

    tools: dict[str, BaseTool] = {"Read": read_file, "Glob": glob, "Grep": grep}
    if include_write:
        tools["Write"] = write_file
    return tools

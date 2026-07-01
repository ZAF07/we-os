"""Filesystem tools — LangChain ``@tool`` adapters over :class:`FilesystemSandbox`.

Each factory closes over a sandbox instance and returns tools keyed by the
Claude-style capability name declared in an agent's frontmatter (``Read``,
``Glob``, ``Grep``, ``Write``). Path-scoping is enforced by the sandbox; a
violation raises :class:`ToolError`, which the agent's tool node converts into a
recoverable error message rather than crashing the run.
"""

from __future__ import annotations

from langchain_core.tools import BaseTool, tool

from marketing_os.adapters.tools.sandbox import FilesystemSandbox


def filesystem_tools(sandbox: FilesystemSandbox, *, include_write: bool) -> dict[str, BaseTool]:
    """Build filesystem tools keyed by Claude-style capability name.

    Args:
        sandbox: The sandbox that resolves and guards every path.
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
    def write_file(path: str, content: str) -> str:
        """Write a UTF-8 text file under ``campaigns/`` to save a deliverable.

        Args:
            path: Path under ``campaigns/``, relative to the repository root.
            content: The full text to write.

        Returns:
            A short confirmation message.
        """
        return sandbox.write(path, content)

    tools: dict[str, BaseTool] = {"Read": read_file, "Glob": glob, "Grep": grep}
    if include_write:
        tools["Write"] = write_file
    return tools

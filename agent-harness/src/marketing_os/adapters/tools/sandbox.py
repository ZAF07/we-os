"""Filesystem sandbox — read-scoping enforced in code, never trusted to the prompt.

Mirrors ``.claude/settings.json``: an agent may **read** anywhere under the repo
root (governance, templates, knowledge, customers, campaigns). Writes do not go
through the sandbox — they go through the :class:`~marketing_os.ports.DocumentStore`
port, guarded by :func:`~marketing_os.adapters.tools.scope.validate_campaign_write`.
"""

from __future__ import annotations

import re
from pathlib import Path

from marketing_os.errors import ToolError

_MAX_GREP_MATCHES = 200
_MAX_READ_BYTES = 400_000


class FilesystemSandbox:
    """Resolves and guards every path a filesystem read tool touches."""

    def __init__(self, root: Path) -> None:
        """Initialise the sandbox.

        Args:
            root: The repository root that bounds all reads.
        """
        self.root = root.resolve()

    def _resolve(self, rel: str) -> Path:
        """Resolve a repo-relative path and reject any escape outside the root.

        Args:
            rel: A path relative to the repository root.

        Returns:
            The resolved absolute path.

        Raises:
            ToolError: If the path escapes the repository root.
        """
        resolved = (self.root / rel).resolve()
        if not resolved.is_relative_to(self.root):
            raise ToolError(f"Path '{rel}' escapes the repository root.")
        return resolved

    def read(self, path: str) -> str:
        """Read a UTF-8 text file under the repository root.

        Args:
            path: A path relative to the repository root.

        Returns:
            The file contents, decoded as UTF-8 and truncated to a byte ceiling.

        Raises:
            ToolError: If the path escapes the root or the file does not exist.
        """
        resolved = self._resolve(path)
        if not resolved.is_file():
            raise ToolError(f"File not found: {path}")
        data = resolved.read_bytes()[:_MAX_READ_BYTES]
        return data.decode("utf-8", errors="replace")

    def glob(self, pattern: str) -> str:
        """List repository files matching a glob pattern.

        Args:
            pattern: A glob pattern relative to the repository root.

        Returns:
            Newline-separated matching paths, or a message when none match.
        """
        matches = sorted(str(match.relative_to(self.root)) for match in self.root.glob(pattern))
        if not matches:
            return f"No files match '{pattern}'."
        return "\n".join(matches[:_MAX_GREP_MATCHES])

    def grep(self, pattern: str, path: str | None = None) -> str:
        """Search repository markdown for a regex, returning ``file:line`` matches.

        Args:
            pattern: The regular expression to search for.
            path: An optional file or directory to narrow the search to.

        Returns:
            Newline-separated ``path:line: text`` matches, or a message when none.

        Raises:
            ToolError: If the regex is invalid or the path escapes the root.
        """
        try:
            compiled = re.compile(pattern)
        except re.error as exc:
            raise ToolError(f"Invalid regex: {exc}") from exc
        base = self._resolve(path) if path else self.root
        files = [base] if base.is_file() else [f for f in base.rglob("*.md") if f.is_file()]
        out: list[str] = []
        for file in files:
            try:
                lines = file.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for line_number, line in enumerate(lines, 1):
                if compiled.search(line):
                    out.append(f"{file.relative_to(self.root)}:{line_number}: {line.strip()}")
                    if len(out) >= _MAX_GREP_MATCHES:
                        return "\n".join(out) + "\n… (truncated)"
        return "\n".join(out) if out else f"No matches for '{pattern}'."

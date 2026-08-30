"""Filesystem sandbox — read-scoping enforced in code, never trusted to the prompt.

Serves the repository's **code-shipped** material: governance, templates,
knowledge and guardrails. Reads are repo-wide within that material and bounded
by the repository root.

Tenant-owned documents are deliberately *not* reachable here. They live under
``tenants/`` and are served only by the tenant-scoped
:class:`~marketing_os.ports.DocumentStore`, so a specialist cannot reach another
business's Brand DNA or deliverables even if its prompt is subverted into asking
(ADR-0013). Writes likewise go through the store, guarded by
:func:`~marketing_os.adapters.tools.scope.validate_campaign_write`.
"""

from __future__ import annotations

import re
from pathlib import Path

from marketing_os.adapters.documents import TENANTS_DIR
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
        self._tenants_root = (self.root / TENANTS_DIR).resolve()

    def _resolve(self, rel: str) -> Path:
        """Resolve a repo-relative path, rejecting escapes and tenant-owned data.

        Args:
            rel: A path relative to the repository root.

        Returns:
            The resolved absolute path.

        Raises:
            ToolError: If the path escapes the repository root, or reaches into
                the tenant document tree, which only the store may serve.
        """
        resolved = (self.root / rel).resolve()
        if not resolved.is_relative_to(self.root):
            raise ToolError(f"Path '{rel}' escapes the repository root.")
        self._refuse_tenant_data(resolved, rel)
        return resolved

    def _refuse_tenant_data(self, resolved: Path, rel: str) -> None:
        """Reject a resolved path that reaches into the tenant document tree.

        Args:
            resolved: The already-resolved absolute path.
            rel: The original path, for the error message.

        Raises:
            ToolError: If the path is inside ``tenants/``.
        """
        if self._is_tenant_data(resolved):
            raise ToolError(
                f"Path '{rel}' is tenant-owned data and is not readable with this tool. "
                "Read the Brand DNA and campaign deliverables by their document paths "
                "('dna.md', 'campaigns/<slug>/<name>.md') instead."
            )

    def _is_tenant_data(self, path: Path) -> bool:
        """Return whether a path lies inside the tenant document tree.

        Args:
            path: The absolute path to test.

        Returns:
            ``True`` when the path is tenant-owned and must not be listed.
        """
        return path == self._tenants_root or path.is_relative_to(self._tenants_root)

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
        matches = sorted(
            str(match.relative_to(self.root))
            for match in self.root.glob(pattern)
            if not self._is_tenant_data(match)
        )
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
        files = (
            [base]
            if base.is_file()
            else [f for f in base.rglob("*.md") if f.is_file() and not self._is_tenant_data(f)]
        )
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

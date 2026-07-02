"""Filesystem sandbox — path-scoping enforced in code, never trusted to the prompt.

Mirrors ``.claude/settings.json``: an agent may **read** anywhere under the repo
root (governance, templates, knowledge, customers, campaigns) but may **write**
only under the configured write prefixes (``campaigns/**``). ``customers/`` is
therefore read-only to agents, exactly as in the Claude Code configuration.
"""

from __future__ import annotations

import re
from pathlib import Path

from marketing_os.errors import ToolError

_MAX_GREP_MATCHES = 200
_MAX_READ_BYTES = 400_000


class FilesystemSandbox:
    """Resolves and guards every path a filesystem tool touches."""

    def __init__(self, root: Path, write_prefixes: list[str] | None = None) -> None:
        """Initialise the sandbox.

        Args:
            root: The repository root that bounds all reads.
            write_prefixes: Glob-ish prefixes whose first path segment defines the
                directories writes are permitted under; defaults to ``["campaigns"]``.
        """
        self.root = root.resolve()
        prefixes = write_prefixes or ["campaigns"]
        self.write_roots = [self.root / prefix.split("/")[0] for prefix in prefixes]

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

    def write(self, path: str, content: str, *, slug: str | None = None) -> str:
        """Write a UTF-8 text file under an allowed write root.

        When ``slug`` is given the write is additionally scoped to that campaign:
        the path must live under ``<write-root>/<slug>/`` (for example
        ``campaigns/<slug>/``). This rejects a mis-slugged path the model
        hallucinated even though it is otherwise a legal write, so the deliverable
        cannot land in the wrong campaign.

        Args:
            path: A path relative to the repository root.
            content: The text to write.
            slug: The live run slug to scope the write to; when ``None`` only the
                write-root guard applies.

        Returns:
            A short confirmation message.

        Raises:
            ToolError: If the path escapes the root, is outside every write root,
                or (when ``slug`` is given) is not under ``<write-root>/<slug>/``.
        """
        resolved = self._resolve(path)
        if not any(resolved.is_relative_to(root) for root in self.write_roots):
            allowed = ", ".join(str(root.relative_to(self.root)) + "/" for root in self.write_roots)
            raise ToolError(
                f"Writes are only permitted under: {allowed}. Refused write to '{path}'."
            )
        if slug is not None:
            scoped_roots = [root / slug for root in self.write_roots]
            if not any(resolved.is_relative_to(scoped) for scoped in scoped_roots):
                used = self._campaign_segment(resolved)
                raise ToolError(
                    f"Write path '{path}' is not under this campaign's directory. You "
                    f"used the slug '{used}', but this run's slug is '{slug}'. Save the "
                    f"deliverable under campaigns/{slug}/ and use the slug '{slug}' "
                    "verbatim, character for character — never alter, abbreviate, or "
                    "guess it."
                )
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} chars to {path}"

    def _campaign_segment(self, resolved: Path) -> str:
        """Return the first path segment under the matching write root.

        Names the slug the model actually used in a rejected write so the error
        message can contrast it with the run slug.

        Args:
            resolved: A path already known to sit under a write root.

        Returns:
            The first path segment beneath its write root, or the empty string.
        """
        for root in self.write_roots:
            if resolved.is_relative_to(root):
                parts = resolved.relative_to(root).parts
                return parts[0] if parts else ""
        return ""

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

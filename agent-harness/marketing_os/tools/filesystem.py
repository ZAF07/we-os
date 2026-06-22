"""Filesystem tools, path-scoped to the Marketing OS repo.

Mirrors the repo's `.claude/settings.json`: the agent may **read** anywhere under
the repo root (governance, templates, knowledge, customers, campaigns) but may
**write** only under `campaigns/**`. `customers/` is therefore read-only to
agents. Scoping is enforced here, never trusted to the prompt.

`FilesystemTools` holds the sandbox and exposes bound methods that the agent
builder registers as ADK FunctionTools.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..errors import ToolError

_MAX_READ_BYTES = 400_000
_MAX_MATCHES = 200


class FilesystemTools:
    """Path-scoped read/write/list/search tools over the repo root."""

    def __init__(self, root: Path, write_prefixes: list[str] | None = None) -> None:
        """Bind the sandbox.

        Args:
            root: Repo root; all paths resolve relative to it.
            write_prefixes: Top-level dirs writes are confined to (default ``campaigns``).
        """
        self.root = root.resolve()
        prefixes = write_prefixes or ["campaigns"]
        self.write_roots = [self.root / p.split("/")[0] for p in prefixes]

    def _resolve(self, rel: str) -> Path:
        """Resolve a repo-relative path, rejecting anything escaping the root."""
        p = (self.root / rel).resolve()
        if not p.is_relative_to(self.root):
            raise ToolError(f"path '{rel}' escapes the repository root")
        return p

    def read_file(self, path: str) -> dict:
        """Read a UTF-8 text file by its repo-relative path.

        Args:
            path: Path relative to the repo root.

        Returns:
            {path, content} or {error}.
        """
        try:
            p = self._resolve(path)
            if not p.is_file():
                return {"error": f"file not found: {path}"}
            return {"path": path, "content": p.read_bytes()[:_MAX_READ_BYTES].decode("utf-8", "replace")}
        except ToolError as exc:
            return {"error": str(exc)}

    def write_file(self, path: str, content: str) -> dict:
        """Write a UTF-8 text file under the allowed write roots (campaigns/**).

        Args:
            path: Repo-relative destination (must be under campaigns/).
            content: File contents.

        Returns:
            {path, bytes_written} or {error} if outside the write scope.
        """
        try:
            p = self._resolve(path)
        except ToolError as exc:
            return {"error": str(exc)}
        if not any(p.is_relative_to(w) for w in self.write_roots):
            allowed = ", ".join(str(w.relative_to(self.root)) + "/" for w in self.write_roots)
            return {"error": f"writes only allowed under: {allowed}"}
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"path": path, "bytes_written": len(content.encode("utf-8"))}

    def list_files(self, pattern: str) -> dict:
        """List files matching a glob pattern relative to the repo root.

        Args:
            pattern: e.g. ``knowledge/**/*.md``.

        Returns:
            {matches:[...]}.
        """
        matches = sorted(str(m.relative_to(self.root)) for m in self.root.glob(pattern) if m.is_file())
        return {"matches": matches[:_MAX_MATCHES]}

    def search_files(self, pattern: str, path: str | None = None) -> dict:
        """Regex-search repository markdown; return file:line matches.

        Args:
            pattern: Python regex.
            path: Optional file or directory to limit the search to.

        Returns:
            {matches:[...]} or {error}.
        """
        try:
            rx = re.compile(pattern)
        except re.error as exc:
            return {"error": f"invalid regex: {exc}"}
        try:
            base = self._resolve(path) if path else self.root
        except ToolError as exc:
            return {"error": str(exc)}
        files = [base] if base.is_file() else [f for f in base.rglob("*.md") if f.is_file()]
        out: list[str] = []
        for f in files:
            try:
                for i, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                    if rx.search(line):
                        out.append(f"{f.relative_to(self.root)}:{i}: {line.strip()}")
                        if len(out) >= _MAX_MATCHES:
                            return {"matches": out}
            except OSError:
                continue
        return {"matches": out}

    def as_tools(self) -> dict:
        """Return capability-name -> bound method, for the per-agent allowlist.

        Keys match agents.yaml: read_file, write_file, list_files, search_files.
        """
        return {
            "read_file": self.read_file,
            "write_file": self.write_file,
            "list_files": self.list_files,
            "search_files": self.search_files,
        }

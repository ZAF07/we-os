"""Filesystem tools, path-scoped to the Marketing OS repo.

Mirrors `.claude/settings.json`: the agent may **read** anywhere under the repo
root (governance, templates, knowledge, customers, campaigns) but may **write**
only under the configured write globs (`campaigns/**`). `customers/` is therefore
read-only to agents, exactly as in the Claude Code config. Scoping is enforced
here in the tool, never trusted to the prompt.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..errors import ToolError
from .registry import Tool

_MAX_GREP_MATCHES = 200
_MAX_READ_BYTES = 400_000


class FilesystemSandbox:
    """Resolves and guards every path a filesystem tool touches."""

    def __init__(self, root: Path, write_prefixes: list[str] | None = None) -> None:
        self.root = root.resolve()
        # Derive allowed write roots from glob-ish prefixes ("campaigns/**" -> "campaigns").
        prefixes = write_prefixes or ["campaigns"]
        self.write_roots = [self.root / p.split("/")[0] for p in prefixes]

    def _resolve(self, rel: str) -> Path:
        p = (self.root / rel).resolve()
        if not p.is_relative_to(self.root):
            raise ToolError(f"Path '{rel}' escapes the repository root.")
        return p

    def read(self, path: str) -> str:
        p = self._resolve(path)
        if not p.is_file():
            raise ToolError(f"File not found: {path}")
        data = p.read_bytes()[:_MAX_READ_BYTES]
        return data.decode("utf-8", errors="replace")

    def write(self, path: str, content: str) -> str:
        p = self._resolve(path)
        if not any(p.is_relative_to(w) for w in self.write_roots):
            allowed = ", ".join(str(w.relative_to(self.root)) + "/" for w in self.write_roots)
            raise ToolError(
                f"Writes are only permitted under: {allowed}. Refused write to '{path}'."
            )
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} chars to {path}"

    def glob(self, pattern: str) -> str:
        matches = sorted(str(m.relative_to(self.root)) for m in self.root.glob(pattern))
        if not matches:
            return f"No files match '{pattern}'."
        return "\n".join(matches[:_MAX_GREP_MATCHES])

    def grep(self, pattern: str, path: str | None = None) -> str:
        try:
            rx = re.compile(pattern)
        except re.error as exc:
            raise ToolError(f"Invalid regex: {exc}") from exc
        base = self._resolve(path) if path else self.root
        files = [base] if base.is_file() else [f for f in base.rglob("*.md") if f.is_file()]
        out: list[str] = []
        for f in files:
            try:
                for i, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                    if rx.search(line):
                        out.append(f"{f.relative_to(self.root)}:{i}: {line.strip()}")
                        if len(out) >= _MAX_GREP_MATCHES:
                            return "\n".join(out) + "\n… (truncated)"
            except OSError:
                continue
        return "\n".join(out) if out else f"No matches for '{pattern}'."


def filesystem_tools(sandbox: FilesystemSandbox, *, include_write: bool) -> dict[str, Tool]:
    """Build the filesystem Tool objects, keyed by Claude-style capability name."""
    read_file = Tool(
        name="read_file",
        description="Read a UTF-8 text file from the repository by its path relative to the repo root.",
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Path relative to repo root."}},
            "required": ["path"],
        },
        fn=lambda path: sandbox.read(path),
    )
    glob_tool = Tool(
        name="glob",
        description="List files matching a glob pattern (relative to the repo root), e.g. 'knowledge/**/*.md'.",
        parameters={
            "type": "object",
            "properties": {"pattern": {"type": "string"}},
            "required": ["pattern"],
        },
        fn=lambda pattern: sandbox.glob(pattern),
    )
    grep_tool = Tool(
        name="grep",
        description="Search repository markdown for a regex; returns file:line matches. Optional path narrows the search.",
        parameters={
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string", "description": "Optional file or directory to search within."},
            },
            "required": ["pattern"],
        },
        fn=lambda pattern, path=None: sandbox.grep(pattern, path),
    )
    tools = {"Read": read_file, "Glob": glob_tool, "Grep": grep_tool}
    if include_write:
        tools["Write"] = Tool(
            name="write_file",
            description="Write a UTF-8 text file under campaigns/. Use this to save your deliverable.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path under campaigns/, relative to repo root."},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
            fn=lambda path, content: sandbox.write(path, content),
        )
    return tools

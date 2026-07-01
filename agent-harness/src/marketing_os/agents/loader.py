"""Load specialist definitions from `.claude/agents/*.md`.

The repo's agent markdown is the single source of truth: YAML frontmatter
(`name`, `description`, `tools`) plus a markdown body that is the system prompt.
This parser keeps the harness and the Claude Code config in lockstep — editing
an agent's markdown changes the harness's behavior with no code change.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from ..config import Settings
from ..errors import ConfigError


@dataclass
class AgentSpec:
    """A parsed specialist definition."""

    name: str
    description: str
    tools: list[str]  # Claude-style capability names: Read, Grep, Glob, Write, WebSearch, WebFetch
    body: str  # the system prompt (markdown after the frontmatter)


def _split_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        raise ConfigError("Agent file is missing YAML frontmatter (no leading '---').")
    # Frontmatter is between the first two '---' fences.
    parts = text.split("\n")
    if parts[0].strip() != "---":
        raise ConfigError("Agent frontmatter must start on the first line with '---'.")
    end = None
    for i in range(1, len(parts)):
        if parts[i].strip() == "---":
            end = i
            break
    if end is None:
        raise ConfigError("Agent frontmatter is not closed with a second '---'.")
    fm = yaml.safe_load("\n".join(parts[1:end])) or {}
    body = "\n".join(parts[end + 1 :]).strip()
    return fm, body


def _parse_tools(raw) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(t).strip() for t in raw if str(t).strip()]
    return [t.strip() for t in str(raw).split(",") if t.strip()]


def load_agent_file(path: Path) -> AgentSpec:
    """Parse a single agent markdown file into an AgentSpec."""
    if not path.is_file():
        raise ConfigError(f"Agent definition not found: {path}")
    fm, body = _split_frontmatter(path.read_text(encoding="utf-8"))
    name = fm.get("name") or path.stem
    return AgentSpec(
        name=str(name),
        description=str(fm.get("description", "")),
        tools=_parse_tools(fm.get("tools")),
        body=body,
    )


def load_agent(settings: Settings, name: str) -> AgentSpec:
    """Load the specialist named `name` from `.claude/agents/<name>.md`."""
    return load_agent_file(settings.agents_dir / f"{name}.md")


def load_all_agents(settings: Settings) -> dict[str, AgentSpec]:
    """Load every specialist definition, keyed by name."""
    if not settings.agents_dir.is_dir():
        raise ConfigError(f"Agents directory not found: {settings.agents_dir}")
    out: dict[str, AgentSpec] = {}
    for path in sorted(settings.agents_dir.glob("*.md")):
        spec = load_agent_file(path)
        out[spec.name] = spec
    return out

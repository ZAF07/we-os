"""Load per-agent configuration from agents.yaml.

Keeps capability/human-check policy as data, not code, so an operator can retune
which tools each agent gets (and where human checks fire) without edits to the
builder.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ..config import Settings


@dataclass
class AgentCfg:
    """Resolved configuration for one stage's agent.

    Attributes:
        key: Stage key (intake, research, ...).
        tools: Capability allowlist (only these are handed to the agent).
        confirm: Capabilities whose calls require human confirmation.
        human_check: Whether to attach the explicit `request_human_approval` tool.
    """

    key: str
    tools: list[str] = field(default_factory=list)
    confirm: list[str] = field(default_factory=list)
    human_check: bool = False


@dataclass
class RegistryConfig:
    """All agent configs plus the approval-gate switch."""

    agents: dict[str, AgentCfg]
    approval_enabled: bool = False


def load_registry(settings: Settings) -> RegistryConfig:
    """Parse agents.yaml into typed configs.

    Args:
        settings: Resolves the packaged agents.yaml path.

    Returns:
        A RegistryConfig with one AgentCfg per stage and the approval switch.
    """
    path: Path = settings.agents_config
    data = yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else {}
    agents_raw = (data or {}).get("agents", {})
    agents = {
        key: AgentCfg(
            key=key,
            tools=list(cfg.get("tools", []) or []),
            confirm=list(cfg.get("confirm", []) or []),
            human_check=bool(cfg.get("human_check", False)),
        )
        for key, cfg in agents_raw.items()
    }
    approval_enabled = bool((data or {}).get("approval", {}).get("enabled", False))
    return RegistryConfig(agents=agents, approval_enabled=approval_enabled)

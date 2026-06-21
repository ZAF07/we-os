"""Runtime configuration for the harness.

Everything that varies between deployments lives here: which provider is active,
the model/endpoint/key for it, where the Marketing OS repo root is, and the loop
and QA limits. Values resolve from environment variables with sensible defaults,
so the same code runs locally, in CI, and in the SaaS backend by changing env
only.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .errors import ConfigError

# ── Repo-root resolution ────────────────────────────────────────────────────
# The harness reads governance from the Marketing OS repo (the directory that
# contains `.claude/`). Default: walk up from this file until we find it.


def _discover_root() -> Path:
    env = os.environ.get("MARKETING_OS_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".claude").is_dir():
            return parent
    # Fallback: parent of the agent-harness/ directory.
    return here.parents[2]


# ── Per-provider connection settings ────────────────────────────────────────


@dataclass
class ProviderConfig:
    """Connection details for one provider adapter."""

    model: str
    api_key: str | None = None
    base_url: str | None = None
    # Anthropic-specific; ignored by chat-completions adapters.
    thinking: bool = True


# Defaults per provider. Model strings/base URLs are overridable by env so no
# guessed value is load-bearing — confirm DeepSeek's exact model id + base URL.
_PROVIDER_DEFAULTS: dict[str, dict[str, str]] = {
    "deepseek": {
        "model_env": "DEEPSEEK_MODEL",
        "model_default": "deepseek-v4-pro",  # CONFIRM: exact DeepSeek model id
        "key_env": "DEEPSEEK_API_KEY",
        "base_url_env": "DEEPSEEK_BASE_URL",
        "base_url_default": "https://api.deepseek.com/v1",  # CONFIRM: exact base URL
    },
    "anthropic": {
        "model_env": "ANTHROPIC_MODEL",
        "model_default": "claude-opus-4-8",
        "key_env": "ANTHROPIC_API_KEY",
        "base_url_env": "ANTHROPIC_BASE_URL",
        "base_url_default": "",
    },
    "openai": {
        "model_env": "OPENAI_MODEL",
        "model_default": "",  # no guessed default — user must set OPENAI_MODEL
        "key_env": "OPENAI_API_KEY",
        "base_url_env": "OPENAI_BASE_URL",
        "base_url_default": "",
    },
}


@dataclass
class Settings:
    """Top-level harness configuration."""

    provider: str = field(default_factory=lambda: os.environ.get("MARKETING_OS_PROVIDER", "deepseek"))
    root: Path = field(default_factory=_discover_root)
    max_steps: int = field(default_factory=lambda: int(os.environ.get("MARKETING_OS_MAX_STEPS", "20")))
    max_qa_iterations: int = field(default_factory=lambda: int(os.environ.get("MARKETING_OS_MAX_QA", "3")))
    stream: bool = field(default_factory=lambda: os.environ.get("MARKETING_OS_STREAM", "1") != "0")
    enable_web: bool = field(default_factory=lambda: os.environ.get("MARKETING_OS_WEB", "0") == "1")

    # ── Derived governance paths ─────────────────────────────────────────────
    @property
    def claude_dir(self) -> Path:
        return self.root / ".claude"

    @property
    def agents_dir(self) -> Path:
        return self.claude_dir / "agents"

    @property
    def rules_dir(self) -> Path:
        return self.claude_dir / "rules"

    @property
    def templates_dir(self) -> Path:
        return self.root / "templates"

    @property
    def customers_dir(self) -> Path:
        return self.root / "customers"

    @property
    def campaigns_dir(self) -> Path:
        return self.root / "campaigns"

    @property
    def knowledge_dir(self) -> Path:
        return self.root / "knowledge"

    @property
    def guardrails_dir(self) -> Path:
        return self.root / "guardrails"

    def provider_config(self, name: str | None = None) -> ProviderConfig:
        """Resolve connection details for `name` (defaults to the active provider)."""
        name = name or self.provider
        spec = _PROVIDER_DEFAULTS.get(name)
        if spec is None:
            raise ConfigError(
                f"Unknown provider '{name}'. Known: {', '.join(_PROVIDER_DEFAULTS)}."
            )
        model = os.environ.get(spec["model_env"], spec["model_default"])
        if not model:
            raise ConfigError(
                f"No model configured for provider '{name}'. "
                f"Set {spec['model_env']}."
            )
        base_url = os.environ.get(spec["base_url_env"], spec["base_url_default"]) or None
        return ProviderConfig(
            model=model,
            api_key=os.environ.get(spec["key_env"]),
            base_url=base_url,
        )

    def validate_root(self) -> None:
        if not self.claude_dir.is_dir():
            raise ConfigError(
                f"Marketing OS root not found at {self.root} (no .claude/ directory). "
                f"Set MARKETING_OS_ROOT."
            )


def load_settings() -> Settings:
    """Build Settings from the environment and validate the repo root."""
    settings = Settings()
    settings.validate_root()
    return settings

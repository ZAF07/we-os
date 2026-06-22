"""Runtime configuration.

Everything that varies between deployments lives here: which provider/model is
active, where the Marketing OS repo root is, the memory store location, and loop
limits. Values resolve from environment variables with sensible defaults, so the
same code runs locally, in CI, and in a SaaS backend by changing env only.

The active model is built from `provider_config()` and handed to ADK via
LiteLLM (see `marketing_os.model`).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .errors import ConfigError


def _discover_root() -> Path:
    """Locate the Marketing OS repo root (the dir containing `.claude/`).

    Honors `MARKETING_OS_ROOT`; otherwise walks up from this file. Falls back to
    the grandparent of the package directory.
    """
    env = os.environ.get("MARKETING_OS_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".claude").is_dir():
            return parent
    return here.parents[2]


@dataclass
class ProviderConfig:
    """LiteLLM connection details for one provider.

    Attributes:
        model: LiteLLM model string, e.g. ``deepseek/deepseek-chat``.
        api_key: Provider API key (also read by LiteLLM from env as a fallback).
        api_base: Optional custom endpoint for OpenAI-compatible providers.
    """

    model: str
    api_key: str | None = None
    api_base: str | None = None


# Providers that ADK runs NATIVELY (bare model string, no LiteLLM wrapper).
# Auth for these is handled by google-genai from the environment — `GOOGLE_API_KEY`
# (AI Studio) or `GOOGLE_GENAI_USE_VERTEXAI=TRUE` + Vertex project/location.
NATIVE_GOOGLE_PROVIDERS = {"gemini", "google"}

# Providers whose API supports a JSON-schema `response_format` (so ADK's
# `output_schema` works as constrained decoding). For others (e.g. DeepSeek, which
# returns "This response_format type is unavailable now"), formatter/evaluator
# agents fall back to prompt-based JSON instead.
STRUCTURED_OUTPUT_PROVIDERS = {"gemini", "google", "openai"}


def supports_structured_output(provider: str) -> bool:
    """Whether `provider` supports ADK `output_schema` (JSON-schema response_format)."""
    return provider in STRUCTURED_OUTPUT_PROVIDERS

# Per-provider defaults. Model strings/base URLs are overridable by env so no
# guessed value is load-bearing — CONFIRM the exact model id for your account.
# Gemini is native (ADK resolves `gemini-*` directly); the rest go via LiteLLM
# (provider prefixes: deepseek/, anthropic/, openai/).
_PROVIDER_DEFAULTS: dict[str, dict[str, str]] = {
    "gemini": {
        "model_env": "GOOGLE_MODEL",
        "model_default": "gemini-2.5-flash",  # CONFIRM/override via GOOGLE_MODEL
        "key_env": "GOOGLE_API_KEY",
        "base_env": "GOOGLE_API_BASE",
        "base_default": "",
    },
    "deepseek": {
        "model_env": "DEEPSEEK_MODEL",
        "model_default": "deepseek/deepseek-chat",  # CONFIRM exact DeepSeek model id
        "key_env": "DEEPSEEK_API_KEY",
        "base_env": "DEEPSEEK_API_BASE",
        "base_default": "",
    },
    "anthropic": {
        "model_env": "ANTHROPIC_MODEL",
        "model_default": "anthropic/claude-opus-4-8",
        "key_env": "ANTHROPIC_API_KEY",
        "base_env": "ANTHROPIC_API_BASE",
        "base_default": "",
    },
    "openai": {
        "model_env": "OPENAI_MODEL",
        "model_default": "openai/gpt-4o",
        "key_env": "OPENAI_API_KEY",
        "base_env": "OPENAI_API_BASE",
        "base_default": "",
    },
}


@dataclass
class Settings:
    """Top-level harness configuration, resolved from the environment."""

    provider: str = field(
        default_factory=lambda: os.environ.get("MARKETING_OS_PROVIDER", "gemini")
    )
    root: Path = field(default_factory=_discover_root)
    app_name: str = field(default_factory=lambda: os.environ.get("MARKETING_OS_APP", "marketing_os"))
    # Loop/limits.
    max_eval_iterations: int = field(
        default_factory=lambda: int(os.environ.get("MARKETING_OS_MAX_EVAL", "3"))
    )
    # Where cross-task memory persists (SQLite file).
    memory_db: Path = field(
        default_factory=lambda: Path(
            os.environ.get("MARKETING_OS_MEMORY_DB", "")
        ).expanduser()
        if os.environ.get("MARKETING_OS_MEMORY_DB")
        else None  # type: ignore[arg-type]
    )

    def __post_init__(self) -> None:
        if self.memory_db is None:
            self.memory_db = self.root / ".marketing_os" / "memory.sqlite3"

    # ── Governance / data paths ───────────────────────────────────────────────
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
        """Repo-root editable professional rubrics the Evaluator scores against."""
        return self.root / "guardrails"

    @property
    def agents_config(self) -> Path:
        """Per-agent tool/human-check config (shipped with the package)."""
        return Path(__file__).resolve().parent / "agents" / "agents.yaml"

    @property
    def prompts_dir(self) -> Path:
        """Agent instruction bodies (markdown), shipped with the package."""
        return Path(__file__).resolve().parent / "agents" / "prompts"

    # ── Provider resolution ────────────────────────────────────────────────────
    def provider_config(self, name: str | None = None) -> ProviderConfig:
        """Resolve the LiteLLM model/key/base for `name` (default: active provider).

        Raises:
            ConfigError: if the provider is unknown or no model is configured.
        """
        name = name or self.provider
        if name == "google":  # alias for the native Gemini provider
            name = "gemini"
        spec = _PROVIDER_DEFAULTS.get(name)
        if spec is None:
            raise ConfigError(
                f"Unknown provider '{name}'. Known: {', '.join(_PROVIDER_DEFAULTS)}."
            )
        model = os.environ.get(spec["model_env"], spec["model_default"])
        if not model:
            raise ConfigError(f"No model configured for '{name}'. Set {spec['model_env']}.")
        base = os.environ.get(spec["base_env"], spec["base_default"]) or None
        return ProviderConfig(model=model, api_key=os.environ.get(spec["key_env"]), api_base=base)

    def validate_root(self) -> None:
        """Raise ConfigError if the repo root has no `.claude/` governance dir."""
        if not self.claude_dir.is_dir():
            raise ConfigError(
                f"Marketing OS root not found at {self.root} (no .claude/). Set MARKETING_OS_ROOT."
            )


def load_settings() -> Settings:
    """Build Settings from the environment and validate the repo root."""
    settings = Settings()
    settings.validate_root()
    return settings

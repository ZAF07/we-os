"""Runtime configuration for the Marketing OS harness.

Everything that varies between deployments resolves here from environment
variables with sensible defaults: which provider and model are active, where the
Marketing OS repo root lives, and the loop and QA limits. The same code therefore
runs locally, in CI, and in a backend by changing environment only.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .errors import ConfigError

_CLAUDE_DIR_NAME = ".claude"


def _discover_root() -> Path:
    """Locate the Marketing OS repository root.

    Resolution order: the ``MARKETING_OS_ROOT`` environment variable if set,
    otherwise the nearest ancestor directory that contains a ``.claude/`` folder,
    otherwise the current working directory as a last resort.

    Returns:
        The resolved absolute path to the repository root.
    """
    env = os.environ.get("MARKETING_OS_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / _CLAUDE_DIR_NAME).is_dir():
            return parent
    return Path.cwd().resolve()


@dataclass
class ProviderConfig:
    """Connection details for one chat-model provider.

    Attributes:
        model: The model identifier passed to the LangChain chat model.
        api_key: The API key, or ``None`` to fall back to the provider SDK default.
        base_url: An override base URL, or ``None`` for the provider default.
    """

    model: str
    api_key: str | None = None
    base_url: str | None = None


_PROVIDER_DEFAULTS: dict[str, dict[str, str]] = {
    "deepseek": {
        "model_env": "DEEPSEEK_MODEL",
        "model_default": "deepseek-chat",
        "key_env": "DEEPSEEK_API_KEY",
        "base_url_env": "DEEPSEEK_BASE_URL",
        "base_url_default": "",
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
        "model_default": "",
        "key_env": "OPENAI_API_KEY",
        "base_url_env": "OPENAI_BASE_URL",
        "base_url_default": "",
    },
}


@dataclass
class Settings:
    """Top-level harness configuration resolved from the environment.

    Attributes:
        provider: The active provider name (``deepseek`` | ``anthropic`` | ``openai``).
        root: The Marketing OS repository root.
        max_steps: The tool-call budget bounding each specialist's inner loop.
        max_qa_iterations: The revision budget for the per-stage QA loop.
        stream: Whether the CLI streams progress events.
        enable_web: Whether web-search tools are wired for agents that declare them.
    """

    provider: str = field(
        default_factory=lambda: os.environ.get("MARKETING_OS_PROVIDER", "deepseek")
    )
    root: Path = field(default_factory=_discover_root)
    max_steps: int = field(
        default_factory=lambda: int(os.environ.get("MARKETING_OS_MAX_STEPS", "20"))
    )
    max_qa_iterations: int = field(
        default_factory=lambda: int(os.environ.get("MARKETING_OS_MAX_QA", "3"))
    )
    stream: bool = field(default_factory=lambda: os.environ.get("MARKETING_OS_STREAM", "1") != "0")
    enable_web: bool = field(default_factory=lambda: os.environ.get("MARKETING_OS_WEB", "0") == "1")

    @property
    def claude_dir(self) -> Path:
        """Return the ``.claude/`` governance directory under the repo root."""
        return self.root / _CLAUDE_DIR_NAME

    @property
    def agents_dir(self) -> Path:
        """Return the directory holding the specialist agent specs."""
        return self.claude_dir / "agents"

    @property
    def rules_dir(self) -> Path:
        """Return the directory holding the canonical governance rules."""
        return self.claude_dir / "rules"

    @property
    def templates_dir(self) -> Path:
        """Return the directory holding the DNA and goal templates."""
        return self.root / "templates"

    @property
    def customers_dir(self) -> Path:
        """Return the directory holding per-customer DNA profiles."""
        return self.root / "customers"

    @property
    def campaigns_dir(self) -> Path:
        """Return the directory where campaign deliverables are written."""
        return self.root / "campaigns"

    @property
    def knowledge_dir(self) -> Path:
        """Return the central domain-knowledge library directory."""
        return self.root / "knowledge"

    @property
    def guardrails_dir(self) -> Path:
        """Return the directory holding the per-stage review rubrics."""
        return self.root / "guardrails"

    def provider_config(
        self, name: str | None = None, *, role: str | None = None
    ) -> ProviderConfig:
        """Resolve connection details for a provider, optionally for a named role.

        A role (for example ``"reviewer"``) may override the model via a
        ``MARKETING_OS_<ROLE>_MODEL`` environment variable so a cheaper judge model
        can be used without changing the active provider.

        Args:
            name: The provider name to resolve; defaults to the active provider.
            role: An optional role whose per-role model override takes precedence.

        Returns:
            The resolved :class:`ProviderConfig`.

        Raises:
            ConfigError: If the provider is unknown or no model is configured.
        """
        name = name or self.provider
        spec = _PROVIDER_DEFAULTS.get(name)
        if spec is None:
            raise ConfigError(f"Unknown provider '{name}'. Known: {', '.join(_PROVIDER_DEFAULTS)}.")
        role_model = os.environ.get(f"MARKETING_OS_{role.upper()}_MODEL") if role else None
        model = role_model or os.environ.get(spec["model_env"], spec["model_default"])
        if not model:
            raise ConfigError(
                f"No model configured for provider '{name}'. Set {spec['model_env']}."
            )
        base_url = os.environ.get(spec["base_url_env"], spec["base_url_default"]) or None
        return ProviderConfig(
            model=model,
            api_key=os.environ.get(spec["key_env"]),
            base_url=base_url,
        )

    def validate_root(self) -> None:
        """Ensure the resolved repository root contains a ``.claude/`` directory.

        Raises:
            ConfigError: If the root is missing its ``.claude/`` directory.
        """
        if not self.claude_dir.is_dir():
            raise ConfigError(
                f"Marketing OS root not found at {self.root} (no .claude/ directory). "
                "Set MARKETING_OS_ROOT."
            )


def load_settings() -> Settings:
    """Build :class:`Settings` from the environment and validate the repo root.

    Returns:
        A validated :class:`Settings` instance.
    """
    settings = Settings()
    settings.validate_root()
    return settings

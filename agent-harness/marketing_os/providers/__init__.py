"""Provider registry + factory.

`get_provider(name, config)` returns a ready adapter. Adapters are imported
lazily so optional vendor SDKs (openai, anthropic) are only required when their
provider is actually selected. Register a custom adapter with `register()`.
"""

from __future__ import annotations

from typing import Callable, Optional

from ..config import ProviderConfig, Settings
from ..errors import ConfigError
from .base import Provider

# name -> zero-arg importer returning the Provider subclass (lazy)
_REGISTRY: dict[str, Callable[[], type[Provider]]] = {}


def register(name: str, importer: Callable[[], type[Provider]]) -> None:
    """Register a provider adapter under `name` (importer returns the class)."""
    _REGISTRY[name] = importer


def _load_deepseek() -> type[Provider]:
    from .deepseek_provider import DeepSeekProvider

    return DeepSeekProvider


def _load_openai() -> type[Provider]:
    from .openai_provider import OpenAIProvider

    return OpenAIProvider


def _load_anthropic() -> type[Provider]:
    from .anthropic_provider import AnthropicProvider

    return AnthropicProvider


register("deepseek", _load_deepseek)
register("openai", _load_openai)
register("anthropic", _load_anthropic)


def get_provider(name: str, config: ProviderConfig) -> Provider:
    """Instantiate the adapter registered under `name`."""
    importer = _REGISTRY.get(name)
    if importer is None:
        raise ConfigError(
            f"No provider adapter registered for '{name}'. "
            f"Known: {', '.join(sorted(_REGISTRY))}."
        )
    return importer()(config)


def provider_from_settings(settings: Settings, name: Optional[str] = None) -> Provider:
    """Build the active (or named) provider using connection details from settings."""
    name = name or settings.provider
    return get_provider(name, settings.provider_config(name))


__all__ = ["Provider", "get_provider", "provider_from_settings", "register"]

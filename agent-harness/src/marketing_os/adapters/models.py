"""Chat-model adapter — the driven adapter over LangChain chat models.

Turns a :class:`~marketing_os.config.Settings` object into a configured
LangChain ``BaseChatModel``. DeepSeek is the primary provider and is built
directly with ``ChatDeepSeek``; every other provider is resolved through
``init_chat_model`` so alternates stay swappable by configuration alone.
"""

from __future__ import annotations

from typing import Any

from langchain_core.language_models import BaseChatModel

from ..config import ProviderConfig, Settings
from ..errors import ProviderError

_DEFAULT_MAX_TOKENS = 16000


def get_model(
    settings: Settings,
    *,
    role: str | None = None,
    max_tokens: int = _DEFAULT_MAX_TOKENS,
) -> BaseChatModel:
    """Build a LangChain chat model for the active provider.

    Args:
        settings: The resolved harness settings selecting the provider and model.
        role: An optional role (for example ``"reviewer"``) whose per-role model
            override is honoured when resolving the model.
        max_tokens: The per-turn output-token ceiling for the model.

    Returns:
        A configured LangChain ``BaseChatModel`` ready to invoke or bind tools to.

    Raises:
        ProviderError: If the provider is unknown or its integration is unavailable.
    """
    config = settings.provider_config(role=role)
    provider = settings.provider
    if provider == "deepseek":
        return _build_deepseek(config, max_tokens)
    return _build_via_init_chat_model(provider, config, max_tokens)


def _build_deepseek(config: ProviderConfig, max_tokens: int) -> BaseChatModel:
    """Build the primary ``ChatDeepSeek`` model from resolved connection details.

    Args:
        config: The resolved provider connection details.
        max_tokens: The per-turn output-token ceiling.

    Returns:
        A configured ``ChatDeepSeek`` instance.

    Raises:
        ProviderError: If ``langchain-deepseek`` is not installed.
    """
    try:
        from langchain_deepseek import ChatDeepSeek
    except ImportError as exc:
        raise ProviderError(
            "The DeepSeek provider requires 'langchain-deepseek'. "
            "Install it with: uv add langchain-deepseek"
        ) from exc
    kwargs: dict[str, Any] = {"model": config.model, "max_tokens": max_tokens}
    if config.api_key:
        kwargs["api_key"] = config.api_key
    if config.base_url:
        kwargs["api_base"] = config.base_url
    return ChatDeepSeek(**kwargs)


def _build_via_init_chat_model(
    provider: str, config: ProviderConfig, max_tokens: int
) -> BaseChatModel:
    """Build a non-primary provider model through ``init_chat_model``.

    Args:
        provider: The provider name understood by ``init_chat_model``.
        config: The resolved provider connection details.
        max_tokens: The per-turn output-token ceiling.

    Returns:
        A configured ``BaseChatModel`` for the requested provider.

    Raises:
        ProviderError: If the provider integration package is not installed.
    """
    from langchain.chat_models import init_chat_model

    kwargs: dict[str, Any] = {"model_provider": provider, "max_tokens": max_tokens}
    if config.api_key:
        kwargs["api_key"] = config.api_key
    if config.base_url:
        kwargs["base_url"] = config.base_url
    try:
        return init_chat_model(config.model, **kwargs)
    except ImportError as exc:
        raise ProviderError(
            f"The '{provider}' provider integration is not installed. "
            f"Install it with: uv add --optional {provider} langchain-{provider}"
        ) from exc

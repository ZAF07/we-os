"""Build the ADK model object from configuration.

Google **Gemini is native** to ADK: a bare model string (e.g. ``gemini-2.5-flash``)
is resolved by ADK directly and authenticated by google-genai from the environment
(`GOOGLE_API_KEY` for AI Studio, or `GOOGLE_GENAI_USE_VERTEXAI=TRUE` + Vertex
project/location). Every other provider (DeepSeek/Claude/OpenAI) goes through ADK's
LiteLLM wrapper. Either way, the rest of the system never imports a vendor SDK —
it just passes the result to `LlmAgent(model=...)`.
"""

from __future__ import annotations

from typing import Optional, Union

from google.adk.models.lite_llm import LiteLlm

from ._compat import apply_patches
from .config import NATIVE_GOOGLE_PROVIDERS, Settings
from .errors import ModelError

# Make ADK tolerant of malformed tool-call JSON (e.g. from DeepSeek) the moment
# the model layer is imported — before any run starts.
apply_patches()


def build_model(settings: Settings, provider: Optional[str] = None) -> Union[str, LiteLlm]:
    """Construct the model for the active (or named) provider.

    Args:
        settings: Resolved harness settings.
        provider: Override the active provider
            (``gemini`` | ``deepseek`` | ``anthropic`` | ``openai``).

    Returns:
        For Gemini, the bare model-id string (ADK resolves it natively). For other
        providers, a `LiteLlm` instance. Both are valid for `LlmAgent(model=...)`.

    Raises:
        ModelError: if the provider config is invalid.
    """
    name = provider or settings.provider
    cfg = settings.provider_config(name)

    # Native path: hand ADK the bare model string; google-genai reads auth from env.
    if name in NATIVE_GOOGLE_PROVIDERS:
        return cfg.model

    # LiteLLM path for non-Google providers. The `model` must be a LiteLLM id
    # (e.g. ``deepseek/deepseek-chat``), NOT an endpoint URL — a common mix-up.
    model = (cfg.model or "").strip()
    model_env = f"{name.upper()}_MODEL"
    base_env = f"{name.upper()}_API_BASE"
    if "://" in model:
        raise ModelError(
            f"{model_env} is set to a URL ('{model}'), but it must be a LiteLLM "
            f"model id like '{name}/<model>' (e.g. 'deepseek/deepseek-chat'). "
            f"Put the endpoint in {base_env} instead — and note DeepSeek/OpenAI "
            f"usually don't need a custom base at all."
        )
    if "/" not in model:
        # Be forgiving: a bare id like 'deepseek-chat' -> 'deepseek/deepseek-chat'.
        model = f"{name}/{model}"

    # api_key/api_base pass straight through; LiteLLM also reads them from env.
    kwargs: dict = {"model": model}
    if cfg.api_key:
        kwargs["api_key"] = cfg.api_key
    if cfg.api_base:
        kwargs["api_base"] = cfg.api_base
    try:
        return LiteLlm(**kwargs)
    except Exception as exc:  # pragma: no cover - construction is config-dependent
        raise ModelError(f"Could not build model for provider '{name}': {exc}") from exc

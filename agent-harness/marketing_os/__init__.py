"""Marketing OS — provider-agnostic agent harness.

Reproduces the governance encoded in the repo's `.claude/` configuration
(Customer DNA gate, mandatory decision pipeline, five specialist agents, and a
per-stage self-critique loop) over direct LLM API access.

Public surface:

    from marketing_os import load_settings, MarketingDirector

    settings = load_settings()
    director = MarketingDirector(settings)
    director.run_campaign("coast-coffee")
"""

from __future__ import annotations

from .config import ProviderConfig, Settings, load_settings
from .errors import (
    ConfigError,
    GateError,
    GuardrailError,
    MarketingOSError,
    PipelineError,
    ProviderError,
    ToolError,
)
from .types import (
    CompletionResult,
    Discrepancy,
    Message,
    ReviewVerdict,
    StageResult,
    ToolCall,
    ToolResult,
    Usage,
)

__all__ = [
    "Settings",
    "ProviderConfig",
    "load_settings",
    "MarketingOSError",
    "ConfigError",
    "GateError",
    "PipelineError",
    "GuardrailError",
    "ToolError",
    "ProviderError",
    "Message",
    "ToolCall",
    "ToolResult",
    "Usage",
    "CompletionResult",
    "Discrepancy",
    "ReviewVerdict",
    "StageResult",
]

# Lazily re-exported to avoid importing optional provider SDKs at package import.
def __getattr__(name: str):  # pragma: no cover - thin lazy shim
    if name == "MarketingDirector":
        from .orchestrator import MarketingDirector

        return MarketingDirector
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

"""Marketing OS — an ADK-native, coordinator-led multi-agent marketing system.

Reproduces the governance of the repo's `.claude/` configuration (Customer DNA
gate, mandatory pipeline, professional guardrails) on Google ADK, with a
coordinator that runs a 9-stage specialist pipeline, real tools (file + Playwright
web browsing), two-tier guardrails, configurable human checks, and persistent
cross-task memory.

Public surface:

    from marketing_os import load_settings, MarketingDirector

    director = MarketingDirector(load_settings())
    await director.run_campaign("coast-coffee")
"""

from __future__ import annotations

from .config import ProviderConfig, Settings, load_settings
from .errors import (
    ApprovalRequired,
    ConfigError,
    GateError,
    GuardrailError,
    MarketingOSError,
    ModelError,
    ToolError,
)
from .schemas import STAGE_SCHEMAS, DecisionEnvelope

__all__ = [
    "Settings",
    "ProviderConfig",
    "load_settings",
    "MarketingOSError",
    "ConfigError",
    "GateError",
    "GuardrailError",
    "ApprovalRequired",
    "ToolError",
    "ModelError",
    "DecisionEnvelope",
    "STAGE_SCHEMAS",
]


def __getattr__(name: str):  # pragma: no cover - thin lazy shim
    """Lazily expose the orchestrator without importing ADK at package import."""
    if name == "MarketingDirector":
        from .orchestrator import MarketingDirector

        return MarketingDirector
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

"""Marketing OS — a LangGraph agent application for the marketing decision pipeline.

Reproduces the governance encoded in the repo's ``.claude/`` configuration (the
Customer DNA gate, the mandatory decision pipeline, the specialist agents, and a
per-stage self-critique loop) as a compiled LangGraph ``StateGraph`` built on
LangChain chat models.

The specialist and review nodes run on the async graph path (ADR-0009), so a run
is driven with ``ainvoke``/``astream`` on the event loop and can be cancelled with
its in-flight LLM calls. The :func:`marketing_os.graph.runner.run_campaign` helper
wraps this for synchronous callers.

Public surface::

    import asyncio

    from marketing_os import load_settings, build_campaign_graph

    settings = load_settings()
    graph = build_campaign_graph(settings)
    result = asyncio.run(
        graph.ainvoke(
            {"customer": "coast-coffee", "slug": "coast-coffee"},
            config={"configurable": {"thread_id": "coast-coffee"}},
        )
    )
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from marketing_os.config import ProviderConfig, Settings, load_settings
from marketing_os.errors import (
    ConfigError,
    GateError,
    GuardrailError,
    MarketingOSError,
    PipelineError,
    ProviderError,
    ToolError,
)
from marketing_os.schemas import (
    CampaignResult,
    Discrepancy,
    ReviewVerdict,
    StageResult,
    Usage,
)

if TYPE_CHECKING:
    from marketing_os.graph.graph import build_campaign_graph, build_single_stage_graph

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
    "Usage",
    "Discrepancy",
    "ReviewVerdict",
    "StageResult",
    "CampaignResult",
    "build_campaign_graph",
    "build_single_stage_graph",
]


def __getattr__(name: str) -> Any:
    """Lazily expose the graph builders without importing LangGraph at import time.

    Args:
        name: The attribute being accessed on the package.

    Returns:
        The requested graph builder callable.

    Raises:
        AttributeError: If the attribute is not a known lazy export.
    """
    if name in {"build_campaign_graph", "build_single_stage_graph"}:
        from marketing_os.graph import graph as _graph_module

        return getattr(_graph_module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

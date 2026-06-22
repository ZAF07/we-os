"""Compatibility patches for ADK provider quirks.

Some providers (notably DeepSeek via LiteLLM) occasionally emit **malformed or
truncated JSON in tool-call arguments**. ADK's
``lite_llm._parse_tool_call_arguments`` tries json → ast → key-repair and then
hard-raises, which aborts the entire pipeline over one bad tool call.

We wrap that function with a final salvage step: best-effort repair of truncated
JSON, and failing that, return ``{}`` so the tool is simply invoked with empty
arguments (it returns an error result the model can recover from) instead of
crashing the run. Idempotent and provider-agnostic.
"""

from __future__ import annotations

import json
from typing import Any

_PATCHED = False


def _salvage(arguments: Any) -> dict:
    """Recover a dict from malformed tool-call argument JSON, or return ``{}``.

    Handles the common failure modes (unterminated string, unclosed object) by
    appending plausible closers; gives up to an empty dict rather than raising.
    """
    if not arguments:
        return {}
    if not isinstance(arguments, str):
        return arguments if isinstance(arguments, dict) else {}
    for suffix in ("", '"', '"}', "}", '"}}', "}}"):
        try:
            obj = json.loads(arguments + suffix)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(obj, dict):
            return obj
    return {}


def apply_patches() -> None:
    """Install the lenient tool-argument parser on ADK's LiteLLM model (once)."""
    global _PATCHED
    if _PATCHED:
        return
    try:
        from google.adk.models import lite_llm
    except Exception:  # pragma: no cover - ADK layout changed
        return
    original = getattr(lite_llm, "_parse_tool_call_arguments", None)
    if original is None:  # pragma: no cover - symbol renamed upstream
        _PATCHED = True
        return

    def lenient(arguments: Any):
        """ADK's parser, but salvaging instead of raising on unrecoverable JSON."""
        try:
            return original(arguments)
        except Exception:
            return _salvage(arguments)

    lite_llm._parse_tool_call_arguments = lenient  # module-global lookup at call site
    _PATCHED = True

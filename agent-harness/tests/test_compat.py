"""The lenient tool-argument parser patch (resilience to malformed provider JSON)."""

from __future__ import annotations

from marketing_os._compat import _salvage, apply_patches


def test_salvage_recovers_or_empties_never_raises():
    assert _salvage('{"path": "research.md"}') == {"path": "research.md"}  # valid
    # Truncated/unterminated string -> repaired to a dict (value may be partial).
    repaired = _salvage('{"path": "campaigns/coast-test/resea')
    assert isinstance(repaired, dict) and "path" in repaired
    # Unclosed object -> closed.
    assert _salvage('{"a": 1') == {"a": 1}
    # Hopeless -> empty dict, not an exception.
    assert _salvage("��� not json at all") == {}
    assert _salvage("") == {}
    assert _salvage(None) == {}


def test_patched_parser_does_not_raise_on_bad_json():
    apply_patches()
    from google.adk.models import lite_llm

    # Valid JSON still parses normally through the wrapped function.
    assert lite_llm._parse_tool_call_arguments('{"x": 2}') == {"x": 2}
    # The exact failure from the traceback no longer crashes — it returns a dict.
    out = lite_llm._parse_tool_call_arguments('{"path": "campaigns/coast-test/resea')
    assert isinstance(out, dict)

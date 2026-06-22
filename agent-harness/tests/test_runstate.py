"""Resume machinery: checkpoint persistence, stage-completion, and skip guards."""

from __future__ import annotations

import json
from types import SimpleNamespace

from marketing_os.agents import make_skip_if_done
from marketing_os.runstate import (
    checkpoint_path,
    clear_checkpoint,
    completed_stages,
    eval_passed,
    load_checkpoint,
    save_checkpoint,
)


def test_checkpoint_roundtrip_and_clear(settings):
    assert load_checkpoint(settings, "acme") is None
    save_checkpoint(settings, "acme", {"intake": {"business": "Acme"}, "research": "findings"})
    assert checkpoint_path(settings, "acme").is_file()
    loaded = load_checkpoint(settings, "acme")
    assert loaded["intake"] == {"business": "Acme"} and loaded["research"] == "findings"
    clear_checkpoint(settings, "acme")
    assert load_checkpoint(settings, "acme") is None


def test_checkpoint_skips_nonserializable_and_internal_keys(settings):
    save_checkpoint(
        settings,
        "acme",
        {"intake": "ok", "temp:scratch": "drop", "_hidden": "drop", "bad": {1, 2, 3}},
    )
    loaded = load_checkpoint(settings, "acme")
    assert loaded == {"intake": "ok"}  # set is non-JSON; temp:/_ filtered


def test_completed_stages_in_pipeline_order():
    state = {"research": "x", "intake": "y", "media": "z", "extra": 1}
    assert completed_stages(state) == ["intake", "research", "media"]


def test_eval_passed_handles_dict_json_and_missing():
    assert eval_passed({"eval": {"passed": True}}) is True
    assert eval_passed({"eval": {"passed": False}}) is False
    assert eval_passed({"eval": json.dumps({"passed": True})}) is True
    assert eval_passed({"eval": "not json"}) is False
    assert eval_passed({}) is False


def test_skip_callback_returns_content_only_when_done():
    cb = make_skip_if_done("intake", lambda s: bool(s.get("intake")))
    # present -> skip (returns Content)
    done = cb(SimpleNamespace(state={"intake": {"x": 1}}))
    assert done is not None and done.parts[0].text.startswith("[resume]")
    # absent -> run (returns None)
    assert cb(SimpleNamespace(state={})) is None


def test_skip_callback_works_with_real_adk_state():
    # ADK passes a State object (not a plain dict); dict(state) raises KeyError: 0,
    # so the callback must use state.to_dict(). Guard against regressing that.
    from google.adk.sessions.state import State

    cb = make_skip_if_done("research", lambda s: bool(s.get("research")))
    present = State(value={"research": "findings"}, delta={})
    assert cb(SimpleNamespace(state=present)) is not None
    absent = State(value={}, delta={})
    assert cb(SimpleNamespace(state=absent)) is None

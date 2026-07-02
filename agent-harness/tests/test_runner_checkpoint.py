"""Runner checkpointer tests: thread ids and caller-supplied persistence.

The CLI and API always let the runner default to a :class:`MemorySaver`; the
persistence seam (used by the Postgres checkpointer in a deployment) is the
``checkpointer`` argument threaded through :func:`run_campaign`. These tests
prove the runner honours a supplied saver so a run is resumable by ``thread_id``.
The live Postgres path stays a manual smoke test — it needs a database — and is
skipped unless a DSN is provided.
"""

from __future__ import annotations

import importlib.util
import os

import pytest
from langgraph.checkpoint.memory import MemorySaver

from conftest import install_scripted_graph
from marketing_os.config import Settings
from marketing_os.graph.runner import run_campaign, thread_id


def test_thread_id_scopes_single_stage_runs() -> None:
    assert thread_id("acme", None) == "acme"
    assert thread_id("acme", "research") == "acme:research"


def test_run_persists_checkpoint_under_thread_id(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_scripted_graph(monkeypatch)
    saver = MemorySaver()
    result = run_campaign(settings, "acme", "acme", stage="research", checkpointer=saver)
    assert result.stages[0].stage == "research"
    config = {"configurable": {"thread_id": thread_id("acme", "research")}}
    stored = saver.get_tuple(config)
    assert stored is not None
    assert stored.checkpoint["channel_values"]["error"] is None


def test_supplied_checkpointer_is_reused_across_runs(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_scripted_graph(monkeypatch)
    saver = MemorySaver()
    run_campaign(settings, "acme", "acme", stage="research", checkpointer=saver)
    first = saver.get_tuple({"configurable": {"thread_id": "acme:research"}})

    run_campaign(settings, "acme", "acme", stage="research", checkpointer=saver)
    second = saver.get_tuple({"configurable": {"thread_id": "acme:research"}})

    assert first is not None and second is not None
    assert second.checkpoint["id"] != first.checkpoint["id"]


@pytest.mark.skipif(
    importlib.util.find_spec("langgraph.checkpoint.postgres") is None
    or not os.environ.get("MARKETING_OS_TEST_POSTGRES_DSN"),
    reason="Postgres checkpointer is a manual smoke test: needs the 'postgres' extra "
    "and MARKETING_OS_TEST_POSTGRES_DSN pointing at a live database.",
)
def test_postgres_checkpointer_persists_run(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    from langgraph.checkpoint.postgres import PostgresSaver

    install_scripted_graph(monkeypatch)
    dsn = os.environ["MARKETING_OS_TEST_POSTGRES_DSN"]
    with PostgresSaver.from_conn_string(dsn) as saver:
        saver.setup()
        run_campaign(settings, "acme", "acme", stage="research", checkpointer=saver)
        stored = saver.get_tuple({"configurable": {"thread_id": "acme:research"}})
    assert stored is not None

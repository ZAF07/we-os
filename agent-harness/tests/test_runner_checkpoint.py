"""Runner checkpointer tests: thread ids and caller-supplied persistence.

The persistence seam is the ``checkpointer`` argument threaded through the
runner; the API supplies a process-wide one and a Postgres deployment supplies a
durable one. These tests prove the runner honours a supplied saver, and that a
thread id names one tenant's campaign rather than a bare slug. The durable
Postgres checkpointer is covered against a real database in ``test_postgres.py``.
"""

from __future__ import annotations

import asyncio

import pytest
from langgraph.checkpoint.memory import MemorySaver

from conftest import SLUG, TENANT, install_scripted_graph
from marketing_os.config import Settings
from marketing_os.graph.runner import arun_campaign, thread_id


def test_thread_id_scopes_threads_by_tenant_and_stage() -> None:
    assert thread_id("org_acme", "acme", None) == "org_acme/acme"
    assert thread_id("org_acme", "acme", "research") == "org_acme/acme:research"


def test_two_tenants_running_the_same_slug_get_separate_threads() -> None:
    """Slugs are chosen by businesses, so a shared checkpointer must not share state."""
    assert thread_id("org_acme", "spring", None) != thread_id("org_rival", "spring", None)


def test_run_persists_checkpoint_under_thread_id(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_scripted_graph(monkeypatch)
    saver = MemorySaver()
    result = asyncio.run(
        arun_campaign(settings, TENANT, SLUG, stage="research", checkpointer=saver)
    )
    assert result.stages[0].stage == "research"
    config = {"configurable": {"thread_id": thread_id(TENANT, SLUG, "research")}}
    stored = saver.get_tuple(config)
    assert stored is not None
    assert stored.checkpoint["channel_values"]["error"] is None


def test_supplied_checkpointer_is_reused_across_runs(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_scripted_graph(monkeypatch)
    saver = MemorySaver()
    asyncio.run(arun_campaign(settings, TENANT, SLUG, stage="research", checkpointer=saver))
    thread = {"configurable": {"thread_id": thread_id(TENANT, SLUG, "research")}}
    first = saver.get_tuple(thread)

    asyncio.run(arun_campaign(settings, TENANT, SLUG, stage="research", checkpointer=saver))
    second = saver.get_tuple(thread)

    assert first is not None and second is not None
    assert second.checkpoint["id"] != first.checkpoint["id"]

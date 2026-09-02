"""What only a real Postgres can prove, against a real containerised Postgres.

The document-store *contract* is covered by the shared conformance suite in
``test_documentstore.py``, which the Postgres adapter joins. This file covers
what an in-memory fake cannot honestly model, and which is therefore exactly
where the expensive bugs live:

- **Row-level security.** Tenant isolation is the highest-severity bug class in
  this work, and a dict cannot demonstrate that a query which *forgot* its
  tenant predicate still returns nothing across tenants.
- **The run claim as a database constraint.** "One active run per campaign" only
  holds across workers if Postgres refuses the second claim; a check-then-insert
  in Python would pass a single-process test and lose the race in production.
- **A checkpointer that survives the process.** The whole reason Postgres is a
  hard prerequisite for approval gates.

Every test here is marked ``slow`` and skips unless
``MARKETING_OS_TEST_POSTGRES=1`` is set, so the fast suite needs no Docker.
"""

from __future__ import annotations

import time
from typing import Any

import pytest

from conftest import OTHER_TENANT, SLUG, TENANT, install_scripted_graph
from marketing_os.adapters.observability import new_run_id
from marketing_os.adapters.postgres import (
    PostgresDocumentStore,
    PostgresRunStore,
    PostgresTenantDirectory,
)
from marketing_os.adapters.postgres.schema import TENANT_SETTING
from marketing_os.config import Settings
from marketing_os.errors import RunConflictError
from marketing_os.graph.checkpoints import clear_campaign_threads, thread_id
from marketing_os.graph.runner import arun_campaign
from marketing_os.schemas import RunRecord

pytestmark = pytest.mark.slow


# --- Row-level security ---------------------------------------------------------


def test_a_query_with_no_tenant_scope_returns_nothing_across_tenants(
    postgres_pool: Any,
) -> None:
    """The backstop: forgetting the tenant predicate leaks nothing, it returns nothing.

    This is deliberately raw SQL with no ``WHERE tenant_id``, which is precisely
    the mistake new code makes. Under the policy it sees only the tenant the
    transaction was scoped to.
    """
    store = PostgresDocumentStore(postgres_pool)
    store.write(TENANT, "dna.md", "# Mine")
    store.write(OTHER_TENANT, "dna.md", "# Theirs")

    with postgres_pool.connection() as connection:
        connection.execute("SELECT set_config(%s, %s, true)", (TENANT_SETTING, TENANT))
        unscoped = connection.execute("SELECT tenant_id, content FROM documents").fetchall()

    assert [(row[0], row[1]) for row in unscoped] == [(TENANT, "# Mine")]


def test_a_transaction_with_no_tenant_set_sees_no_documents_at_all(
    postgres_pool: Any,
) -> None:
    """Failing closed matters more than failing loudly: unscoped means empty, never all."""
    PostgresDocumentStore(postgres_pool).write(TENANT, "dna.md", "# Mine")

    with postgres_pool.connection() as connection:
        rows = connection.execute("SELECT tenant_id FROM documents").fetchall()

    assert rows == []


def test_one_tenant_cannot_write_a_row_labelled_as_another(postgres_pool: Any) -> None:
    """The policy's ``WITH CHECK`` half — isolation covers writes, not only reads."""
    import psycopg

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with postgres_pool.connection() as connection:
            connection.execute("SELECT set_config(%s, %s, true)", (TENANT_SETTING, TENANT))
            connection.execute(
                "INSERT INTO documents (tenant_id, path, content) VALUES (%s, %s, %s)",
                (OTHER_TENANT, "dna.md", "# Smuggled"),
            )


def test_the_store_cannot_read_another_tenants_document(postgres_pool: Any) -> None:
    store = PostgresDocumentStore(postgres_pool)
    store.write(TENANT, "campaigns/spring/research.md", "# Mine")

    assert store.exists(OTHER_TENANT, "campaigns/spring/research.md") is False
    assert store.list(OTHER_TENANT, "campaigns/spring") == []


# --- The tenant directory -------------------------------------------------------


def test_the_clerk_organization_id_lives_in_a_column_not_in_the_tenant_id(
    postgres_pool: Any,
) -> None:
    """The pairing this table exists for: a platform id, a name, and the IdP's id."""
    directory = PostgresTenantDirectory(postgres_pool)

    tenant = directory.resolve(external_auth_id="org_3IlR", name="Coast Coffee")

    assert tenant.tenant_id.startswith("ten_")
    assert tenant.external_auth_id == "org_3IlR"
    assert directory.get(tenant.tenant_id) == tenant


def test_resolving_the_same_organization_twice_reuses_its_tenant(postgres_pool: Any) -> None:
    """Two workers seeing a business's first request must not mint two tenants."""
    directory = PostgresTenantDirectory(postgres_pool)

    first = directory.resolve(external_auth_id="org_3IlR", name="Coast Coffee")
    second = PostgresTenantDirectory(postgres_pool).resolve(
        external_auth_id="org_3IlR", name="Coast Coffee Roasters"
    )

    assert second.tenant_id == first.tenant_id
    assert second.name == "Coast Coffee Roasters"


# --- The shared run claim -------------------------------------------------------


def _record(run_id: str, *, tenant: str = TENANT, slug: str = SLUG, worker: str) -> RunRecord:
    """Build a running run record.

    Args:
        run_id: The run's id.
        tenant: The tenant the run belongs to.
        slug: The campaign the run claims.
        worker: The worker claiming it.

    Returns:
        The record to claim.
    """
    now = time.time()
    return RunRecord(
        run_id=run_id,
        tenant_id=tenant,
        slug=slug,
        stage=None,
        status="running",
        worker_id=worker,
        started_at=now,
        heartbeat_at=now,
    )


def test_a_second_worker_is_refused_the_same_campaign(postgres_pool: Any) -> None:
    """Two stores, two workers, one database — the constraint is what holds."""
    first_worker = PostgresRunStore(postgres_pool)
    second_worker = PostgresRunStore(postgres_pool)
    held = new_run_id()
    first_worker.claim(_record(held, worker="wrk_a"))

    with pytest.raises(RunConflictError) as refused:
        second_worker.claim(_record(new_run_id(), worker="wrk_b"))

    assert refused.value.active_run_id == held


def test_finishing_a_run_frees_its_campaign_for_another_worker(postgres_pool: Any) -> None:
    store = PostgresRunStore(postgres_pool)
    first = new_run_id()
    store.claim(_record(first, worker="wrk_a"))

    store.finish(first, "completed")
    second = new_run_id()
    store.claim(_record(second, worker="wrk_b"))

    assert store.active_for_campaign(TENANT, SLUG) is not None
    assert store.active_for_campaign(TENANT, SLUG).run_id == second
    assert store.get(first, TENANT).status == "completed"


def test_two_tenants_may_hold_the_same_slug_at_once(postgres_pool: Any) -> None:
    store = PostgresRunStore(postgres_pool)
    mine = new_run_id()
    theirs = new_run_id()

    store.claim(_record(mine, worker="wrk_a"))
    store.claim(_record(theirs, tenant=OTHER_TENANT, worker="wrk_a"))

    assert [record.run_id for record in store.active(TENANT)] == [mine]
    assert [record.run_id for record in store.active(OTHER_TENANT)] == [theirs]


def test_a_run_belonging_to_another_tenant_is_unfindable(postgres_pool: Any) -> None:
    store = PostgresRunStore(postgres_pool)
    run_id = new_run_id()
    store.claim(_record(run_id, worker="wrk_a"))

    assert store.get(run_id, OTHER_TENANT) is None


def test_a_run_a_dead_worker_left_running_is_reclaimed(postgres_pool: Any) -> None:
    """Survives a restart: the run is resolved, not left ``running`` forever."""
    store = PostgresRunStore(postgres_pool)
    abandoned = new_run_id()
    store.claim(_record(abandoned, worker="wrk_dead"))

    reclaimed = store.reclaim_stale(now=time.time(), stale_after=0.0, status="interrupted")

    assert [record.run_id for record in reclaimed] == [abandoned]
    assert store.get(abandoned, TENANT).status == "interrupted"
    assert store.active_for_campaign(TENANT, SLUG) is None


def test_a_heartbeated_run_is_left_alone_by_a_restarting_peer(postgres_pool: Any) -> None:
    store = PostgresRunStore(postgres_pool)
    live = new_run_id()
    store.claim(_record(live, worker="wrk_live"))
    store.heartbeat([live], time.time())

    reclaimed = store.reclaim_stale(now=time.time(), stale_after=60.0, status="interrupted")

    assert reclaimed == []
    assert store.get(live, TENANT).status == "running"


def test_a_late_callback_cannot_resurrect_a_cancelled_run(postgres_pool: Any) -> None:
    """The worker's own task finishing must not overwrite a cancellation it lost."""
    store = PostgresRunStore(postgres_pool)
    run_id = new_run_id()
    store.claim(_record(run_id, worker="wrk_a"))
    store.finish(run_id, "cancelled")

    store.finish(run_id, "completed")

    assert store.get(run_id, TENANT).status == "cancelled"


# --- The durable checkpointer ---------------------------------------------------


async def test_a_run_checkpoint_outlives_the_process_that_wrote_it(
    settings: Settings,
    postgres_superuser_dsn: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The hard prerequisite for approval gates: state a later process can resume.

    Two savers, opened and closed independently, stand in for two processes: the
    second reads what the first wrote, which an in-process checkpointer cannot do.
    The saver is the **async** one because the runner drives the graph with
    ``astream`` (ADR-0009) — the synchronous saver has no async methods at all.
    """
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    install_scripted_graph(monkeypatch)
    thread = {"configurable": {"thread_id": thread_id(TENANT, SLUG, "research")}}

    async with AsyncPostgresSaver.from_conn_string(postgres_superuser_dsn) as writer:
        await writer.setup()
        await arun_campaign(settings, TENANT, SLUG, stage="research", checkpointer=writer)

    async with AsyncPostgresSaver.from_conn_string(postgres_superuser_dsn) as reader:
        stored = await reader.aget_tuple(thread)

    assert stored is not None
    assert stored.checkpoint["channel_values"]["error"] is None


async def test_clearing_a_campaigns_threads_removes_its_durable_state(
    settings: Settings,
    postgres_superuser_dsn: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Abandoning a cancelled run has to reach the database, not just a dict."""
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    install_scripted_graph(monkeypatch)
    thread = {"configurable": {"thread_id": thread_id(TENANT, SLUG, "research")}}

    async with AsyncPostgresSaver.from_conn_string(postgres_superuser_dsn) as saver:
        await saver.setup()
        await arun_campaign(settings, TENANT, SLUG, stage="research", checkpointer=saver)
        assert await saver.aget_tuple(thread) is not None

        await clear_campaign_threads(saver, TENANT, SLUG)

        assert await saver.aget_tuple(thread) is None

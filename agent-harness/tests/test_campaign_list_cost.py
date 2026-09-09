"""What listing a tenant's campaigns is allowed to cost.

The list behind Home, Campaigns and Calendar is read on nearly every page, so
its cost is the one the whole product pays. Two properties are pinned here and
nowhere else, because both are invisible to a test that only checks the body:

- **Bounded reads.** The number of database statements a list issues must not
  grow with the number of campaigns. Asserted by counting statements against a
  real Postgres adapter for one campaign and for fifty.
- **A list does not stall the engine.** The store calls are synchronous, so a
  long list run on the event loop would hold up every other request behind it.
  Asserted by timing a second request issued while a large list is in flight.

The response itself is pinned by ``test_campaigns_api.py``; what is added here
is a fixture comparison over a mixed portfolio, so a change that makes the list
cheaper cannot quietly change what it says.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from conftest import (
    COMPLETE_GOAL_BODY as COMPLETE_GOAL,
)
from conftest import (
    SLUG,
    TENANT,
    authenticate,
    clear_prototype_adapters,
    install_prototype_adapters,
    install_scripted_graph,
    write_all_agent_specs,
)
from marketing_os.config import Settings


class CountingConnection:
    """Wraps a pooled connection, counting every statement executed on it."""

    def __init__(self, connection: Any, statements: list[str]) -> None:
        """Initialise the wrapper.

        Args:
            connection: The real pooled connection.
            statements: The shared list every executed statement is appended to.
        """
        self._connection = connection
        self._statements = statements

    def execute(self, query: str, *args: Any, **kwargs: Any) -> Any:
        """Record a statement and run it on the wrapped connection.

        Args:
            query: The SQL to execute.
            *args: Positional arguments for the real ``execute``.
            **kwargs: Keyword arguments for the real ``execute``.

        Returns:
            Whatever the real ``execute`` returns.
        """
        self._statements.append(query)
        return self._connection.execute(query, *args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        """Delegate anything else to the wrapped connection.

        Args:
            name: The attribute to read.

        Returns:
            The wrapped connection's attribute.
        """
        return getattr(self._connection, name)


class CountingPool:
    """Wraps a connection pool so a test can count the statements a call issues."""

    def __init__(self, pool: Any) -> None:
        """Initialise the wrapper.

        Args:
            pool: The real ``psycopg_pool.ConnectionPool``.
        """
        self._pool = pool
        self.statements: list[str] = []

    def connection(self) -> Any:
        """Return a context manager yielding a counting connection.

        Returns:
            A context manager over the wrapped pool's connection.
        """
        from contextlib import contextmanager

        @contextmanager
        def _counting() -> Iterator[Any]:
            with self._pool.connection() as connection:
                yield CountingConnection(connection, self.statements)

        return _counting()

    def __getattr__(self, name: str) -> Any:
        """Delegate anything else to the wrapped pool.

        Args:
            name: The attribute to read.

        Returns:
            The wrapped pool's attribute.
        """
        return getattr(self._pool, name)


def _seed_campaigns(documents: Any, count: int, *, tenant: str = TENANT) -> list[str]:
    """Write ``count`` campaign goals straight to the store.

    Seeding through the store rather than the API keeps the setup out of the
    measurement, and the list derives campaigns from the goal documents anyway.

    Args:
        documents: The document store to write into.
        count: How many campaigns to write.
        tenant: The tenant that owns them.

    Returns:
        The slugs written, in the order they were written.
    """
    from marketing_os.campaign.goal import CampaignGoal, render_campaign_goal

    slugs = []
    for index in range(count):
        slug = f"campaign-{index:03d}"
        goal = CampaignGoal(**{**COMPLETE_GOAL, "name": f"Campaign {index}"})
        documents.write(tenant, f"campaigns/{slug}/goal.md", render_campaign_goal(goal))
        slugs.append(slug)
    return slugs


@pytest.fixture
def client(repo: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Yield a hermetic API client over the prototype adapters.

    Args:
        repo: The hermetic repository root fixture.
        monkeypatch: The pytest monkeypatch fixture.

    Yields:
        An entered FastAPI test client.
    """
    monkeypatch.setenv("MARKETING_OS_ROOT", str(repo))
    install_scripted_graph(monkeypatch)
    from marketing_os.entrypoints.api.app import app, get_settings

    get_settings.cache_clear()
    install_prototype_adapters(repo)
    authenticate(app)
    with TestClient(app) as entered:
        yield entered
    get_settings.cache_clear()
    clear_prototype_adapters()


def test_the_list_is_identical_across_a_mixed_portfolio(client: TestClient) -> None:
    """Draft, part-way, stale, approved and archived campaigns all read as before."""
    from marketing_os.entrypoints.api.app import get_deliverable_store, get_document_store
    from marketing_os.governance.pipeline import PIPELINE

    stages = [stage.key for stage in PIPELINE]
    deliverables = get_deliverable_store()
    slugs = _seed_campaigns(get_document_store(), 5)

    for stage_key in stages[:3]:
        deliverables.append(TENANT, slugs[1], stage_key, f"# {stage_key}")
    for stage_key in stages:
        deliverables.append(TENANT, slugs[2], stage_key, f"# {stage_key}")
    for stage_key in stages:
        deliverables.append(TENANT, slugs[3], stage_key, f"# {stage_key}")
    deliverables.append(TENANT, slugs[3], stages[0], "# reopened")
    client.post(f"/campaigns/{slugs[4]}/archive")

    campaigns = client.get("/campaigns").json()["campaigns"]
    by_id = {campaign["id"]: campaign for campaign in campaigns}

    assert slugs[4] not in by_id
    assert by_id[slugs[0]]["status"] == "draft"
    assert by_id[slugs[0]]["stage_progress"] == {
        "completed": 0,
        "total": len(stages),
        "current_stage_key": stages[0],
    }
    assert by_id[slugs[0]]["blocked_reason"] is None
    assert by_id[slugs[1]]["status"] == "running"
    assert by_id[slugs[1]]["stage_progress"]["completed"] == 3
    assert by_id[slugs[1]]["stage_progress"]["current_stage_key"] == stages[3]
    assert by_id[slugs[2]]["status"] == "approved"
    assert by_id[slugs[2]]["stage_progress"]["completed"] == len(stages)
    assert by_id[slugs[3]]["status"] == "running"
    assert by_id[slugs[3]]["blocked_reason"] is not None
    assert "re-opened" in by_id[slugs[3]]["blocked_reason"]


def test_a_campaign_waiting_on_a_person_says_so_in_the_list(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The awaiting-approval case, which needs a real run halted at a gate.

    Read through the same handler as every other status, so the bulk path is
    exercised for the one campaign state that costs a checkpoint read.
    """
    monkeypatch.setenv("MARKETING_OS_ROOT", str(repo))
    write_all_agent_specs(Settings(root=repo))
    install_scripted_graph(monkeypatch)
    from marketing_os.entrypoints.api.app import app, get_settings

    get_settings.cache_clear()
    install_prototype_adapters(repo)
    authenticate(app)

    try:
        with TestClient(app) as client:
            run_id = client.post(f"/campaigns/{SLUG}/run", json={}).json()["run_id"]
            for _ in range(300):
                if client.get(f"/runs/{run_id}").json()["status"] == "awaiting_approval":
                    break
                time.sleep(0.02)
            else:
                raise AssertionError("the run never reached a gate")

            listed = client.get("/campaigns").json()["campaigns"]
            campaign = next(entry for entry in listed if entry["id"] == SLUG)
            single = client.get(f"/campaigns/{SLUG}").json()

    finally:
        get_settings.cache_clear()
        clear_prototype_adapters()

    assert campaign["status"] == "awaiting_approval"
    assert campaign["blocked_reason"] is not None
    assert "approval" in campaign["blocked_reason"]
    assert campaign["status"] == single["status"]
    assert campaign["stage_progress"]["current_stage_key"] == next(
        stage["key"] for stage in single["stages"] if stage["state"] != "completed"
    )


def test_an_archived_campaign_stays_off_the_list(client: TestClient) -> None:
    from marketing_os.entrypoints.api.app import get_document_store

    slugs = _seed_campaigns(get_document_store(), 3)
    before = [campaign["id"] for campaign in client.get("/campaigns").json()["campaigns"]]
    assert set(slugs) <= set(before)
    client.post(f"/campaigns/{slugs[1]}/archive")
    after = [campaign["id"] for campaign in client.get("/campaigns").json()["campaigns"]]
    assert after == [slug for slug in before if slug != slugs[1]]


@pytest.mark.slow
def test_listing_costs_the_same_number_of_statements_at_1_and_50_campaigns(
    postgres_pool: Any, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The list's read count is bounded: it must not grow with the portfolio."""
    from marketing_os.adapters.postgres import PostgresDeliverableStore, PostgresDocumentStore
    from marketing_os.entrypoints.api.app import app, get_settings, use_backend

    monkeypatch.setenv("MARKETING_OS_ROOT", str(repo))
    install_scripted_graph(monkeypatch)
    get_settings.cache_clear()

    counting = CountingPool(postgres_pool)
    backend = _PoolBackend(counting, repo)
    use_backend(backend)
    authenticate(app)

    documents = PostgresDocumentStore(postgres_pool)
    deliverables = PostgresDeliverableStore(postgres_pool)

    try:
        with TestClient(app) as client:
            _seed_campaigns(documents, 1)
            deliverables.append(TENANT, "campaign-000", "research", "# r")
            counting.statements.clear()
            assert client.get("/campaigns").status_code == 200
            with_one = len(counting.statements)

            _seed_campaigns(documents, 50)
            for index in range(50):
                deliverables.append(TENANT, f"campaign-{index:03d}", "research", "# r")
            counting.statements.clear()
            assert client.get("/campaigns").status_code == 200
            with_fifty = len(counting.statements)
    finally:
        use_backend(None)
        get_settings.cache_clear()

    assert with_fifty == with_one, (
        f"listing cost {with_one} statements for 1 campaign and {with_fifty} for 50"
    )


async def test_a_concurrent_request_is_answered_while_a_large_list_is_in_flight(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A slow list must not hold the event loop against every other request.

    The document store is deliberately slowed so one list takes seconds of
    synchronous work — the shape a hundred-campaign portfolio has in production.
    An unrelated request must be *answered* while that list is still running, not
    merely soon after it: the assertion is on the order the two finish in.
    """
    monkeypatch.setenv("MARKETING_OS_ROOT", str(repo))
    install_scripted_graph(monkeypatch)
    from marketing_os.entrypoints.api.app import (
        app,
        get_document_store,
        get_registry,
        get_settings,
    )

    get_settings.cache_clear()
    get_registry.cache_clear()
    install_prototype_adapters(repo)
    authenticate(app)

    store = get_document_store()
    _seed_campaigns(store, 100)
    _slow_down_reads(store, monkeypatch, ("read", "read_many", "exists", "list"), seconds=0.002)
    _slow_down_reads(get_registry(), monkeypatch, ("active",), seconds=0.5)

    transport = ASGITransport(app=app)
    listing_done = asyncio.Event()
    latencies: list[float] = []
    try:
        async with AsyncClient(transport=transport, base_url="http://engine") as client:

            async def _list() -> Any:
                try:
                    return await client.get("/campaigns")
                finally:
                    listing_done.set()

            async def _gate_repeatedly() -> list[Any]:
                """Ask an unrelated question over and over until the list is done."""
                responses = []
                while not listing_done.is_set():
                    started = time.perf_counter()
                    responses.append(await client.get(f"/campaigns/{SLUG}/gate"))
                    latencies.append(time.perf_counter() - started)
                return responses

            listed, gates = await asyncio.gather(_list(), _gate_repeatedly())
    finally:
        get_settings.cache_clear()
        clear_prototype_adapters()

    assert listed.status_code == 200
    assert len(listed.json()["campaigns"]) >= 100
    assert all(gate.status_code == 200 for gate in gates)
    assert len(gates) > 1, "the list finished before a single concurrent request was tried"
    assert max(latencies) < 0.25, (
        f"an unrelated request waited {max(latencies):.2f}s behind the list"
    )


def _slow_down_reads(
    store: Any, monkeypatch: pytest.MonkeyPatch, names: tuple[str, ...], *, seconds: float
) -> None:
    """Make the named reads block, so a list's synchronous cost is visible.

    Every read the list makes is slowed, the registry's included: one left on the
    event loop is enough to stall the engine, so the test must be able to see it.

    Args:
        store: The object whose reads to slow.
        monkeypatch: The pytest monkeypatch fixture.
        names: The method names to slow.
        seconds: How long each read blocks for.
    """
    for name in names:
        original = getattr(store, name)

        def _slow(*args: Any, _original: Any = original, **kwargs: Any) -> Any:
            time.sleep(seconds)
            return _original(*args, **kwargs)

        monkeypatch.setattr(store, name, _slow)


class _PoolBackend:
    """A Postgres backend over a pool a test supplies, with an in-memory checkpointer.

    The counting test needs its own wrapped pool and no checkpointer connection,
    which the real backend opens for itself.
    """

    def __init__(self, pool: Any, root: Path) -> None:
        """Initialise the backend.

        Args:
            pool: The pool every adapter is built over.
            root: The hermetic repository root, for the usage ledger's settings.
        """
        from langgraph.checkpoint.memory import MemorySaver

        from marketing_os.adapters.postgres import (
            PostgresAnswerStore,
            PostgresDeliverableStore,
            PostgresDocumentStore,
            PostgresQuestionnaireStore,
            PostgresRunStore,
            PostgresTenantDirectory,
            PostgresUsageLedger,
        )
        from marketing_os.config import Settings

        self.documents = PostgresDocumentStore(pool)
        self.deliverables = PostgresDeliverableStore(pool)
        self.tenants = PostgresTenantDirectory(pool)
        self.runs = PostgresRunStore(pool)
        self.questionnaires = PostgresQuestionnaireStore(pool)
        self.answers = PostgresAnswerStore(pool)
        self.usage = PostgresUsageLedger(pool, Settings(root=root))
        self.checkpointer = MemorySaver()

    async def open(self) -> None:
        """Do nothing: the pool this backend was handed is already open."""

    async def close(self) -> None:
        """Do nothing: the test owns the pool's lifetime."""

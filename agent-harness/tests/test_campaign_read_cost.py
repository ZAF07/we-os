"""What creating and reading one campaign is allowed to cost.

Issue 03 pinned the campaign list: bounded reads, and none of them on the event
loop. This file pins the same two properties for the paths that describe *one*
campaign — creating it, reading it for its Workspace, archiving it — because
every Workspace open and every "Create campaign" click pays them.

- **Bounded reads.** Reading one campaign issues the same number of statements
  whether one stage has produced work or every stage has, asserted by counting
  statements against a real Postgres adapter.
- **Neither path stalls the engine.** The store reads and the create's write
  are synchronous, so left on the event loop they would hold up every other
  request behind them. Asserted by timing gate reads issued while a slowed
  creation and a slowed read are both in flight.

The payload itself is pinned to the list path, the way 03 pinned the list to
it: the two derivations must agree about every campaign, whatever its status.
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
    CountingPool,
    PoolBackend,
    authenticate,
    clear_prototype_adapters,
    install_prototype_adapters,
    install_scripted_graph,
    seed_campaigns,
    slow_down_reads,
    write_all_agent_specs,
)
from marketing_os.config import Settings


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


def _progress_of(stages: list[dict[str, Any]]) -> dict[str, object]:
    """Summarise a single-campaign payload's stages the way the list does.

    Args:
        stages: The campaign's stages in pipeline order.

    Returns:
        The list's ``stage_progress`` shape, derived from the single payload.
    """
    completed = [stage for stage in stages if stage["state"] == "completed"]
    current = next((stage for stage in stages if stage["state"] != "completed"), None)
    return {
        "completed": len(completed),
        "total": len(stages),
        "current_stage_key": current["key"] if current else None,
    }


def test_the_single_campaign_payload_agrees_with_the_list_across_a_mixed_portfolio(
    client: TestClient,
) -> None:
    """Draft, part-way, approved, stale and archived read the same on both paths."""
    from marketing_os.entrypoints.api.app import get_deliverable_store, get_document_store
    from marketing_os.governance.pipeline import PIPELINE

    stages = [stage.key for stage in PIPELINE]
    deliverables = get_deliverable_store()
    slugs = seed_campaigns(get_document_store(), 5)

    for stage_key in stages[:3]:
        deliverables.append(TENANT, slugs[1], stage_key, f"# {stage_key}")
    for stage_key in stages:
        deliverables.append(TENANT, slugs[2], stage_key, f"# {stage_key}")
    for stage_key in stages:
        deliverables.append(TENANT, slugs[3], stage_key, f"# {stage_key}")
    deliverables.append(TENANT, slugs[3], stages[0], "# reopened")
    for stage_key in stages:
        deliverables.append(TENANT, slugs[4], stage_key, f"# {stage_key}")
    client.post(f"/campaigns/{slugs[4]}/archive")

    listed = {campaign["id"]: campaign for campaign in client.get("/campaigns").json()["campaigns"]}

    for slug in slugs[:4]:
        single = client.get(f"/campaigns/{slug}").json()
        assert single["status"] == listed[slug]["status"], slug
        assert _progress_of(single["stages"]) == listed[slug]["stage_progress"], slug
        assert single["name"] == listed[slug]["name"]
        assert single["objective"] == listed[slug]["objective"]
        report = client.get(f"/campaigns/{slug}/stages").json()
        assert report["status"] == single["status"]
        assert report["stages"] == single["stages"]

    assert [stage["stale"] for stage in client.get(f"/campaigns/{slugs[3]}").json()["stages"]][
        1:
    ] == [True] * (len(stages) - 1)

    archived = client.get(f"/campaigns/{slugs[4]}").json()
    assert slugs[4] not in listed
    assert archived["status"] == "archived"
    assert all(stage["state"] == "completed" for stage in archived["stages"])

    for slug in slugs:
        gate = client.get(f"/campaigns/{slug}/gate").json()
        assert gate == {"ok": True, "issues": []}, slug


def test_a_campaign_waiting_on_a_person_reads_the_same_on_every_path(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The awaiting-approval case, which needs a real run halted at a gate.

    The single read, the stage report and the list must all say the campaign
    is waiting, and name the same stage — the one state that costs a checkpoint
    read on every path.
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

            single = client.get(f"/campaigns/{SLUG}").json()
            report = client.get(f"/campaigns/{SLUG}/stages").json()
            listed = next(
                entry
                for entry in client.get("/campaigns").json()["campaigns"]
                if entry["id"] == SLUG
            )
    finally:
        get_settings.cache_clear()
        clear_prototype_adapters()

    assert single["status"] == "awaiting_approval"
    assert report["status"] == single["status"] == listed["status"]
    assert report["stages"] == single["stages"]
    assert _progress_of(single["stages"]) == listed["stage_progress"]
    waiting = [stage["key"] for stage in single["stages"] if stage["state"] == "awaiting_approval"]
    assert waiting == [listed["stage_progress"]["current_stage_key"]]


def test_a_created_campaign_reads_back_exactly_as_it_was_returned(client: TestClient) -> None:
    """Creation describes the campaign without reading it back; the two must agree."""
    created = client.post("/campaigns", json=COMPLETE_GOAL).json()

    assert client.get(f"/campaigns/{created['id']}").json() == created


def test_reading_an_unknown_campaign_is_a_404_on_every_path(client: TestClient) -> None:
    """A slug the tenant does not own is absent, whichever endpoint asks."""
    assert client.get("/campaigns/never-created").status_code == 404
    assert client.get("/campaigns/never-created/stages").status_code == 404
    assert client.post("/campaigns/never-created/archive").status_code == 404


@pytest.mark.slow
def test_reading_one_campaign_costs_the_same_number_of_statements_whatever_it_has_produced(
    postgres_pool: Any, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The read costs a fixed few statements, with every stage's newest version in one."""
    from marketing_os.adapters.postgres import PostgresDeliverableStore, PostgresDocumentStore
    from marketing_os.entrypoints.api.app import app, get_settings, use_backend
    from marketing_os.governance.pipeline import PIPELINE

    monkeypatch.setenv("MARKETING_OS_ROOT", str(repo))
    install_scripted_graph(monkeypatch)
    get_settings.cache_clear()

    counting = CountingPool(postgres_pool)
    use_backend(PoolBackend(counting, repo))
    authenticate(app)

    documents = PostgresDocumentStore(postgres_pool)
    deliverables = PostgresDeliverableStore(postgres_pool)
    stages = [stage.key for stage in PIPELINE]

    try:
        with TestClient(app) as client:
            (slug,) = seed_campaigns(documents, 1)
            deliverables.append(TENANT, slug, stages[0], "# r")
            counting.statements.clear()
            assert client.get(f"/campaigns/{slug}").status_code == 200
            with_one_stage = len(counting.statements)

            for stage_key in stages:
                deliverables.append(TENANT, slug, stage_key, f"# {stage_key}")
            counting.statements.clear()
            assert client.get(f"/campaigns/{slug}").status_code == 200
            with_every_stage = len(counting.statements)
            deliverable_reads = [
                statement
                for statement in counting.statements
                if statement.startswith("SELECT") and "deliverable_versions" in statement
            ]
    finally:
        use_backend(None)
        get_settings.cache_clear()

    assert with_every_stage == with_one_stage, (
        f"reading cost {with_one_stage} statements with one stage produced and "
        f"{with_every_stage} with every stage produced"
    )
    assert len(deliverable_reads) == 1, (
        f"the newest version of every stage should be one read, not {len(deliverable_reads)}"
    )


async def test_a_gate_read_is_answered_while_a_slowed_create_and_read_are_in_flight(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Neither creating nor reading a campaign may hold the event loop.

    Every store call the two paths make is slowed except the ones the gate
    itself makes, so a call left on the event loop shows up as gate latency
    rather than as a slower gate. An unrelated request must be *answered* while
    both are still running, not merely soon after.
    """
    monkeypatch.setenv("MARKETING_OS_ROOT", str(repo))
    install_scripted_graph(monkeypatch)
    from marketing_os.entrypoints.api.app import (
        app,
        get_deliverable_store,
        get_document_store,
        get_registry,
        get_settings,
    )

    get_settings.cache_clear()
    get_registry.cache_clear()
    install_prototype_adapters(repo)
    authenticate(app)

    slow_down_reads(get_document_store(), monkeypatch, ("list", "write", "read_many"), seconds=0.4)
    slow_down_reads(get_deliverable_store(), monkeypatch, ("latest_by_campaign",), seconds=0.4)
    slow_down_reads(get_registry(), monkeypatch, ("active_for_campaign",), seconds=0.4)

    transport = ASGITransport(app=app)
    slow_paths_done = asyncio.Event()
    latencies: list[float] = []
    try:
        async with AsyncClient(transport=transport, base_url="http://engine") as client:

            async def _create_and_read() -> tuple[Any, Any]:
                """Run the two slowed paths together, marking when both are done."""
                try:
                    return await asyncio.gather(
                        client.post("/campaigns", json=COMPLETE_GOAL),
                        client.get(f"/campaigns/{SLUG}"),
                    )
                finally:
                    slow_paths_done.set()

            async def _gate_repeatedly() -> list[Any]:
                """Ask an unrelated question over and over until both are done."""
                responses = []
                while not slow_paths_done.is_set():
                    started = time.perf_counter()
                    responses.append(await client.get(f"/campaigns/{SLUG}/gate"))
                    latencies.append(time.perf_counter() - started)
                return responses

            (created, read), gates = await asyncio.gather(_create_and_read(), _gate_repeatedly())
    finally:
        get_settings.cache_clear()
        clear_prototype_adapters()

    assert created.status_code == 201
    assert read.status_code == 200
    assert all(gate.status_code == 200 for gate in gates)
    assert len(gates) > 1, "both paths finished before a single concurrent request was tried"
    assert max(latencies) < 0.25, (
        f"an unrelated request waited {max(latencies):.2f}s behind a create or a read"
    )

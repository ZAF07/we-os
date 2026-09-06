"""HTTP tests for the campaign resource: create, list, read and archive.

These cover what the operator's new-campaign wizard and campaign list depend on:
that a campaign created through the interface passes the DNA Gate and can start a
run, that incomplete input is refused by name, that slugs stay unique within a
tenant, and that archiving takes a campaign off the active list without
destroying it.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

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
)


@pytest.fixture
def client(repo: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Yield a hermetic API client with the scripted graph installed.

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


def _without(field: str) -> dict[str, object]:
    """Build the complete goal body with one top-level field blanked.

    Args:
        field: The field to blank.

    Returns:
        The request body.
    """
    return {**COMPLETE_GOAL, field: ""}


def test_create_campaign_returns_the_created_campaign_in_draft(client: TestClient) -> None:
    response = client.post("/campaigns", json=COMPLETE_GOAL)

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == "spring-refill-push"
    assert body["name"] == "Spring Refill Push"
    assert body["status"] == "draft"
    assert body["audience_segment"] == COMPLETE_GOAL["audience_segment"]
    assert body["kpis"] == COMPLETE_GOAL["kpis"]
    assert [stage["key"] for stage in body["stages"]] == [
        "research",
        "brand-strategy",
        "campaign-strategy",
        "performance-plan",
        "creative-brief",
        "asset-prompts",
    ]


def test_a_created_campaign_passes_the_dna_gate(client: TestClient) -> None:
    slug = client.post("/campaigns", json=COMPLETE_GOAL).json()["id"]

    report = client.get(f"/campaigns/{slug}/gate").json()

    assert report["ok"] is True, report["issues"]


def test_a_created_campaign_can_start_a_run(client: TestClient) -> None:
    slug = client.post("/campaigns", json=COMPLETE_GOAL).json()["id"]

    started = client.post(f"/campaigns/{slug}/run", json={"stage": "research"})

    assert started.status_code == 202


def test_create_campaign_writes_the_goal_the_specialists_read(
    client: TestClient, repo: Path
) -> None:
    slug = client.post("/campaigns", json=COMPLETE_GOAL).json()["id"]

    goal = (repo / "tenants" / TENANT / "campaigns" / slug / "goal.md").read_text(encoding="utf-8")

    assert "**Primary business objective:** 120 refill subscriptions in 8 weeks" in goal
    assert "**Creative KPI:** 30% hook rate on launch video" in goal


@pytest.mark.parametrize("field", ["name", "objective", "audience_segment"])
def test_create_campaign_names_the_missing_field(client: TestClient, field: str) -> None:
    response = client.post("/campaigns", json=_without(field))

    assert response.status_code == 422
    body = response.json()
    assert body["type"] == "validation"
    assert field in body["message"]


def test_create_campaign_names_a_missing_kpi_tier(client: TestClient) -> None:
    body = {**COMPLETE_GOAL, "kpis": {**COMPLETE_GOAL["kpis"], "creative": ""}}  # type: ignore[dict-item]

    response = client.post("/campaigns", json=body)

    assert response.status_code == 422
    assert "kpis.creative" in response.json()["message"]


def test_create_campaign_names_every_missing_field_not_only_the_first(
    client: TestClient,
) -> None:
    response = client.post("/campaigns", json={**COMPLETE_GOAL, "name": "", "objective": ""})

    message = response.json()["message"]
    assert "name" in message
    assert "objective" in message


def test_create_campaign_rejects_a_segment_the_brand_dna_does_not_name(
    client: TestClient,
) -> None:
    response = client.post(
        "/campaigns", json={**COMPLETE_GOAL, "audience_segment": "Invented segment"}
    )

    assert response.status_code == 422
    assert "audience_segment" in response.json()["message"]


def test_campaign_slugs_stay_unique_within_a_tenant(client: TestClient) -> None:
    first = client.post("/campaigns", json=COMPLETE_GOAL).json()["id"]
    second = client.post("/campaigns", json=COMPLETE_GOAL).json()["id"]

    assert first == "spring-refill-push"
    assert second == "spring-refill-push-2"


def test_list_campaigns_reports_status_and_stage_progress(client: TestClient) -> None:
    client.post("/campaigns", json=COMPLETE_GOAL)

    body = client.get("/campaigns").json()

    listed = {campaign["id"]: campaign for campaign in body["campaigns"]}
    assert "spring-refill-push" in listed
    created = listed["spring-refill-push"]
    assert created["name"] == "Spring Refill Push"
    assert created["status"] == "draft"
    assert created["stage_progress"] == {
        "completed": 0,
        "total": 6,
        "current_stage_key": "research",
    }


def test_list_campaigns_includes_a_campaign_authored_outside_the_wizard(
    client: TestClient,
) -> None:
    """A hand-authored goal is a campaign too — the list reads the store, not a registry."""
    ids = [campaign["id"] for campaign in client.get("/campaigns").json()["campaigns"]]

    assert SLUG in ids


def test_get_campaign_returns_its_goal_fields(client: TestClient) -> None:
    slug = client.post("/campaigns", json=COMPLETE_GOAL).json()["id"]

    body = client.get(f"/campaigns/{slug}").json()

    assert body["objective"] == COMPLETE_GOAL["objective"]
    assert body["timeframe"] == COMPLETE_GOAL["timeframe"]
    assert body["budget"] == {"amount": 4000.0, "currency": "SGD"}


def test_get_campaign_404s_for_a_slug_the_tenant_does_not_own(client: TestClient) -> None:
    assert client.get("/campaigns/ghost").status_code == 404


def test_archive_campaign_reports_it_archived(client: TestClient) -> None:
    slug = client.post("/campaigns", json=COMPLETE_GOAL).json()["id"]

    response = client.post(f"/campaigns/{slug}/archive")

    assert response.status_code == 200
    assert response.json()["status"] == "archived"


def test_an_archived_campaign_leaves_the_active_list(client: TestClient) -> None:
    slug = client.post("/campaigns", json=COMPLETE_GOAL).json()["id"]
    client.post(f"/campaigns/{slug}/archive")

    ids = [campaign["id"] for campaign in client.get("/campaigns").json()["campaigns"]]

    assert slug not in ids


def test_an_archived_campaign_stays_readable(client: TestClient) -> None:
    """Archiving is a lifecycle change; the campaign and its deliverables survive it."""
    slug = client.post("/campaigns", json=COMPLETE_GOAL).json()["id"]
    client.post(f"/campaigns/{slug}/archive")

    body = client.get(f"/campaigns/{slug}").json()

    assert body["status"] == "archived"
    assert body["objective"] == COMPLETE_GOAL["objective"]


def test_archive_404s_for_a_slug_the_tenant_does_not_own(client: TestClient) -> None:
    assert client.post("/campaigns/ghost/archive").status_code == 404


def test_segments_endpoint_offers_what_the_brand_dna_names(client: TestClient) -> None:
    body = client.get("/brand-dna/segments").json()

    assert body["segments"] == ["Urban 22-35 beginners curious about climbing"]

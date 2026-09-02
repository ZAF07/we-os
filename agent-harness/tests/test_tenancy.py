"""Tenancy tests — the guarantees ADR-0013 buys, exercised at every layer.

Covers the four things that must hold for one business's work to stay its own:
authentication is required, no operation accepts a business identity from the
caller, tenant scoping is enforced inside storage rather than at call sites, and
a resource belonging to another tenant is indistinguishable from one that does
not exist.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from conftest import (
    OTHER_TENANT,
    PLACEHOLDER_DNA,
    SLUG,
    TENANT,
    authenticate,
    install_scripted_graph,
)
from marketing_os.adapters.documents import FilesystemDocumentStore, InMemoryDocumentStore
from marketing_os.adapters.tools.sandbox import FilesystemSandbox
from marketing_os.config import Settings
from marketing_os.errors import DocumentNotFoundError, ToolError


def _client(repo: Path, tenant: str) -> TestClient:
    """Build a hermetic API client acting as a given tenant.

    Args:
        repo: The hermetic repository root.
        tenant: The tenant the injected identity acts for.

    Returns:
        A configured (not yet entered) test client.
    """
    from marketing_os.entrypoints.api.app import app, get_settings, reset_providers

    get_settings.cache_clear()
    reset_providers()
    authenticate(app, tenant)
    return TestClient(app)


# --- Authentication is required -------------------------------------------------


def test_every_route_except_health_refuses_a_request_with_no_token(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without a token the API answers 401 — and never falls open to a default tenant."""
    monkeypatch.setenv("MARKETING_OS_ROOT", str(repo))
    from marketing_os.entrypoints.api.app import app, get_settings, reset_providers

    get_settings.cache_clear()
    reset_providers()
    app.dependency_overrides.clear()

    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        for method, path in [
            ("get", "/me"),
            ("get", f"/campaigns/{SLUG}/gate"),
            ("get", f"/campaigns/{SLUG}/deliverables"),
            ("get", "/runs"),
        ]:
            response = getattr(client, method)(path)
            assert response.status_code == 401, path
            assert response.json()["type"] == "unauthenticated"

    get_settings.cache_clear()
    reset_providers()


def test_a_malformed_authorization_header_is_refused(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MARKETING_OS_ROOT", str(repo))
    monkeypatch.setenv("MARKETING_OS_AUTH_ISSUER", "https://example.clerk.accounts.dev")
    from marketing_os.entrypoints.api.app import app, get_settings, get_token_verifier

    get_settings.cache_clear()
    get_token_verifier.cache_clear()
    app.dependency_overrides.clear()

    with TestClient(app) as client:
        for header in ["", "Bearer", "Bearer ", "Basic abc123", "not-a-scheme token"]:
            response = client.get("/me", headers={"Authorization": header})
            assert response.status_code == 401, header

    get_settings.cache_clear()
    get_token_verifier.cache_clear()


# --- No operation accepts a business identity -----------------------------------


def test_no_request_schema_accepts_a_business_identity(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The OpenAPI schema is the machine-checkable form of ADR-0013's rule."""
    monkeypatch.setenv("MARKETING_OS_ROOT", str(repo))
    with _client(repo, TENANT) as client:
        schema = client.get("/openapi.json").json()

    forbidden = {"tenant", "tenant_id", "customer", "customer_id", "business", "business_id", "org"}

    for path, operations in schema["paths"].items():
        for method, operation in operations.items():
            for parameter in operation.get("parameters", []):
                assert parameter["name"] not in forbidden, f"{method.upper()} {path}"

    for name, component in schema["components"]["schemas"].items():
        for field in component.get("properties", {}):
            assert field not in forbidden, f"{name}.{field}"


def test_a_caller_supplied_tenant_in_the_body_is_ignored(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Even if a client sends one, the tenant comes only from the verified claim."""
    monkeypatch.setenv("MARKETING_OS_ROOT", str(repo))
    with _client(repo, TENANT) as client:
        response = client.post("/campaigns", json={"slug": "smuggled", "tenant": OTHER_TENANT})
        assert response.status_code == 200

    assert (repo / "tenants" / TENANT / "campaigns" / "smuggled" / "goal.md").is_file()
    assert not (repo / "tenants" / OTHER_TENANT).exists()


# --- Scoping is enforced in the storage layer -----------------------------------


def test_filesystem_store_cannot_return_another_tenants_document(tmp_path: Path) -> None:
    """There is no call shape that reaches another tenant's document."""
    store = FilesystemDocumentStore(tmp_path)
    store.write(TENANT, "dna.md", "# Mine")
    store.write(OTHER_TENANT, "dna.md", "# Theirs")

    assert store.read(TENANT, "dna.md") == "# Mine"
    assert store.read(OTHER_TENANT, "dna.md") == "# Theirs"
    assert store.list(TENANT, "campaigns") == []


def test_in_memory_store_cannot_return_another_tenants_document() -> None:
    store = InMemoryDocumentStore()
    store.write(TENANT, "campaigns/spring/research.md", "# Mine")

    assert store.exists(TENANT, "campaigns/spring/research.md")
    assert not store.exists(OTHER_TENANT, "campaigns/spring/research.md")
    assert store.list(OTHER_TENANT, "campaigns/spring") == []
    with pytest.raises(DocumentNotFoundError):
        store.read(OTHER_TENANT, "campaigns/spring/research.md")


@pytest.mark.parametrize(
    "path",
    [
        "../org_rival/dna.md",
        "../../tenants/org_rival/dna.md",
        "campaigns/../../org_rival/dna.md",
        "/etc/passwd",
    ],
)
def test_a_document_path_cannot_climb_out_of_its_tenant(tmp_path: Path, path: str) -> None:
    """Traversal is refused at the store, not merely discouraged by convention."""
    store = FilesystemDocumentStore(tmp_path)
    store.write(OTHER_TENANT, "dna.md", "# Theirs")

    with pytest.raises(ToolError):
        store.read(TENANT, path)


def test_an_invalid_tenant_id_cannot_escape_the_tenants_tree(tmp_path: Path) -> None:
    store = FilesystemDocumentStore(tmp_path)
    for tenant in ["", "..", "../other", "a/b"]:
        with pytest.raises(ToolError):
            store.write(tenant, "dna.md", "# Nope")


# --- The read sandbox serves no tenant data -------------------------------------


def test_the_read_sandbox_refuses_tenant_owned_documents(repo: Path) -> None:
    """A subverted prompt cannot read another business's DNA through the read tool."""
    sandbox = FilesystemSandbox(repo)

    assert "Operating Principles" in sandbox.read(".claude/rules/operating-principles.md")

    with pytest.raises(ToolError):
        sandbox.read(f"tenants/{TENANT}/dna.md")
    with pytest.raises(ToolError):
        sandbox.read(f"tenants/{OTHER_TENANT}/dna.md")


def test_glob_and_grep_never_surface_tenant_data(repo: Path) -> None:
    sandbox = FilesystemSandbox(repo)

    assert "tenants/" not in sandbox.glob("**/*.md")
    assert "tenants/" not in sandbox.grep("Acme Climbing Gym")


# --- Cross-tenant access is indistinguishable from absence ----------------------


def test_another_tenants_campaign_is_404_not_403(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A foreign slug answers exactly as a nonexistent one does, so nothing leaks."""
    monkeypatch.setenv("MARKETING_OS_ROOT", str(repo))

    with _client(repo, OTHER_TENANT) as rival:
        foreign = rival.get(f"/campaigns/{SLUG}/deliverables")
        missing = rival.get("/campaigns/never-existed/deliverables")

    assert foreign.status_code == missing.status_code == 404
    assert foreign.json()["type"] == missing.json()["type"] == "not_found"


def test_a_deliverables_content_is_readable_only_by_its_owner(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The deliverable can be read back — and only by the tenant that owns it."""
    monkeypatch.setenv("MARKETING_OS_ROOT", str(repo))
    document = repo / "tenants" / TENANT / "campaigns" / SLUG / "research.md"
    document.write_text("# Findings\n\nBeginners want coached intros.\n", encoding="utf-8")

    with _client(repo, TENANT) as owner:
        response = owner.get(f"/campaigns/{SLUG}/deliverables/research.md")
        assert response.status_code == 200
        assert "coached intros" in response.json()["content"]

    with _client(repo, OTHER_TENANT) as rival:
        assert rival.get(f"/campaigns/{SLUG}/deliverables/research.md").status_code == 404


def test_a_deliverable_name_cannot_traverse_out_of_the_campaign(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MARKETING_OS_ROOT", str(repo))
    with _client(repo, TENANT) as client:
        for name in ["..%2Fdna.md", "..", "dna.md", "goal.txt"]:
            assert client.get(f"/campaigns/{SLUG}/deliverables/{name}").status_code == 404, name


def test_another_tenants_run_is_not_readable_listable_or_cancellable(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MARKETING_OS_ROOT", str(repo))
    install_scripted_graph(monkeypatch)

    with _client(repo, TENANT) as owner:
        started = owner.post(f"/campaigns/{SLUG}/run", json={"stage": "research"})
        assert started.status_code == 202
        run_id = started.json()["run_id"]
        for _ in range(200):
            if owner.get(f"/runs/{run_id}").json().get("status") == "completed":
                break
        assert owner.get(f"/runs/{run_id}").status_code == 200

    with _client(repo, OTHER_TENANT) as rival:
        assert rival.get(f"/runs/{run_id}").status_code == 404
        assert rival.get(f"/runs/{run_id}/stream").status_code == 404
        assert rival.post(f"/runs/{run_id}/cancel").status_code == 404
        assert rival.get(f"/campaigns/{SLUG}/runs").json()["runs"] == []


def test_the_gate_reports_only_the_callers_own_dna(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The rival has no DNA at all, so their gate fails even though the owner's passes."""
    monkeypatch.setenv("MARKETING_OS_ROOT", str(repo))

    with _client(repo, TENANT) as owner:
        assert owner.get(f"/campaigns/{SLUG}/gate").json()["ok"] is True

    with _client(repo, OTHER_TENANT) as rival:
        report = rival.get(f"/campaigns/{SLUG}/gate").json()
        assert report["ok"] is False
        assert any("Brand DNA" in issue for issue in report["issues"])


def test_me_reports_the_verified_identity(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MARKETING_OS_ROOT", str(repo))
    with _client(repo, TENANT) as client:
        body = client.get("/me").json()

    assert body["user_id"] == f"usr_{TENANT}"
    assert body["business_name"] == "Acme Climbing Gym"
    assert "tenant_id" not in body, "the tenant id is an internal partition key, not client-facing"


def test_the_api_fails_closed_when_no_issuer_is_configured(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing issuer must refuse requests, never silently disable tenancy."""
    monkeypatch.setenv("MARKETING_OS_ROOT", str(repo))
    monkeypatch.delenv("MARKETING_OS_AUTH_ISSUER", raising=False)
    monkeypatch.delenv("CLERK_ISSUER_URL", raising=False)
    from marketing_os.entrypoints.api.app import app, get_settings, get_token_verifier

    get_settings.cache_clear()
    get_token_verifier.cache_clear()
    app.dependency_overrides.clear()

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/me", headers={"Authorization": "Bearer some.jwt.token"})

    assert response.status_code == 500
    get_settings.cache_clear()
    get_token_verifier.cache_clear()


# --- The Stage 0 gate still blocks on an incomplete Brand DNA -------------------


def test_the_dna_gate_still_blocks_a_run_and_names_every_missing_field(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The gate survives the tenancy change: an incomplete DNA refuses the run."""
    monkeypatch.setenv("MARKETING_OS_ROOT", str(repo))
    (repo / "tenants" / TENANT / "dna.md").write_text(PLACEHOLDER_DNA, encoding="utf-8")

    with _client(repo, TENANT) as client:
        response = client.post(f"/campaigns/{SLUG}/run", json={"stage": "research"})

    assert response.status_code == 409
    detail = response.json()
    assert detail["type"] == "gate_failed"
    assert detail["missing_fields"], "the gate names the fields that are missing"
    assert not (repo / "tenants" / TENANT / "campaigns" / SLUG / "research.md").is_file()


# --- The CLI takes its tenant from configuration, never an argument -------------


def test_the_cli_refuses_to_run_without_a_configured_tenant(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from marketing_os.entrypoints.cli import main

    monkeypatch.setenv("MARKETING_OS_ROOT", str(repo))
    monkeypatch.delenv("MARKETING_OS_TENANT_ID", raising=False)

    code = main(["check", SLUG])
    err = capsys.readouterr().err

    assert code == 1
    assert "MARKETING_OS_TENANT_ID" in err


def test_the_cli_accepts_no_tenant_argument() -> None:
    """``new-campaign`` takes a slug and nothing that names a business."""
    from marketing_os.entrypoints.cli import build_parser

    parsed = build_parser().parse_args(["new-campaign", "spring", "--stage", "research"])

    assert parsed.slug == "spring"
    assert not hasattr(parsed, "name")
    assert not hasattr(parsed, "tenant")


def test_settings_expose_no_customer_vocabulary() -> None:
    """'customer' means a person the business sells to — never the business itself."""
    settings = Settings()
    assert not [name for name in dir(settings) if "customer" in name.lower()]

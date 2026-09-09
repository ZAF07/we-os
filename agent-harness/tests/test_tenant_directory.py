"""The tenant directory: the IdP's organization id is data, not the partition key.

Clerk names a business ``org_3IlR...``. Before this slice that string *was* the
tenant id — it named the ``tenants/`` directory, and would have named the
Postgres partition, the run rows and the checkpoint threads. That welds the
platform's identifiers to one identity provider account: swap IdP, re-create an
organization, or migrate a business, and every path is wrong.

So the directory translates once. These tests pin both halves of that: the
adapters' own behaviour, and — the part that actually matters — that a request
authenticated with an organization id stores its documents under the **platform**
tenant id.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from conftest import (
    COMPLETE_GOAL_BODY,
    clear_prototype_adapters,
    install_prototype_adapters,
)
from marketing_os.adapters.tenants import (
    InMemoryTenantDirectory,
    PassthroughTenantDirectory,
)
from marketing_os.errors import TierAlreadySetError, ToolError, UnauthenticatedError
from marketing_os.schemas import RECOMMENDED_TIER, TIER_NAMES, Tenant, VerifiedClaims

CLERK_ORG = "org_3IlRVjdAue93iyWDYAQYGLHcjBx"


# --- The minting directory ------------------------------------------------------


def test_a_business_is_registered_under_a_platform_id_on_first_sight() -> None:
    directory = InMemoryTenantDirectory()

    tenant = directory.resolve(external_auth_id=CLERK_ORG, name="Coast Coffee")

    assert tenant.tenant_id.startswith("ten_")
    assert tenant.tenant_id != CLERK_ORG
    assert tenant.external_auth_id == CLERK_ORG
    assert tenant.name == "Coast Coffee"


def test_the_same_organization_resolves_to_the_same_tenant_every_time() -> None:
    """A business's tenant id must be stable — every document it owns is keyed by it."""
    directory = InMemoryTenantDirectory()

    first = directory.resolve(external_auth_id=CLERK_ORG, name="Coast Coffee")
    second = directory.resolve(external_auth_id=CLERK_ORG, name="Coast Coffee")

    assert first.tenant_id == second.tenant_id


def test_renaming_the_organization_updates_the_name_but_not_the_tenant_id() -> None:
    directory = InMemoryTenantDirectory()
    original = directory.resolve(external_auth_id=CLERK_ORG, name="Coast Coffee")

    renamed = directory.resolve(external_auth_id=CLERK_ORG, name="Coast Coffee Roasters")

    assert renamed.tenant_id == original.tenant_id
    assert renamed.name == "Coast Coffee Roasters"


def test_two_organizations_get_two_tenants() -> None:
    directory = InMemoryTenantDirectory()

    mine = directory.resolve(external_auth_id=CLERK_ORG)
    theirs = directory.resolve(external_auth_id="org_someone_else")

    assert mine.tenant_id != theirs.tenant_id


def test_a_tenant_is_findable_by_its_platform_id() -> None:
    directory = InMemoryTenantDirectory()
    registered = directory.resolve(external_auth_id=CLERK_ORG, name="Coast Coffee")

    assert directory.get(registered.tenant_id) == registered
    assert directory.get("ten_never_registered") is None


def test_an_organization_with_no_name_falls_back_to_its_own_id() -> None:
    """A tenant is never nameless, so support and admin listings always read."""
    directory = InMemoryTenantDirectory()

    assert directory.resolve(external_auth_id=CLERK_ORG).name == CLERK_ORG


@pytest.mark.parametrize("empty", ["", "   "])
def test_an_empty_organization_id_is_refused(empty: str) -> None:
    for directory in (InMemoryTenantDirectory(), PassthroughTenantDirectory()):
        with pytest.raises(ToolError):
            directory.resolve(external_auth_id=empty)


# --- The passthrough directory --------------------------------------------------


def test_the_passthrough_directory_keeps_the_filesystem_layout_working() -> None:
    """Local development has no table to mint ids in, so the two ids stay equal."""
    tenant = PassthroughTenantDirectory().resolve(external_auth_id=CLERK_ORG, name="Coast Coffee")

    assert tenant.tenant_id == CLERK_ORG
    assert tenant.external_auth_id == CLERK_ORG


# --- The tier -------------------------------------------------------------------


def test_a_business_that_has_never_set_a_tier_reports_none() -> None:
    directory = InMemoryTenantDirectory()

    assert directory.resolve(external_auth_id=CLERK_ORG, name="Coast Coffee").tier is None


def test_setting_a_tier_where_none_exists_records_it() -> None:
    directory = InMemoryTenantDirectory()
    tenant = directory.resolve(external_auth_id=CLERK_ORG, name="Coast Coffee")

    recorded = directory.set_tier(tenant.tenant_id, "command")

    assert recorded.tier == "command"
    assert recorded.tenant_id == tenant.tenant_id
    found = directory.get(tenant.tenant_id)
    assert found is not None and found.tier == "command"
    assert directory.resolve(external_auth_id=CLERK_ORG, name="Coast Coffee").tier == "command"


def test_repeating_the_recorded_tier_succeeds_and_changes_nothing() -> None:
    """The welcome flow retries the tier call alone, so the retry must be harmless."""
    directory = InMemoryTenantDirectory()
    tenant = directory.resolve(external_auth_id=CLERK_ORG, name="Coast Coffee")
    first = directory.set_tier(tenant.tenant_id, "operator")

    again = directory.set_tier(tenant.tenant_id, "operator")

    assert again == first


def test_naming_a_different_tier_is_refused() -> None:
    """A tier is set once: changing it is a billing event, and billing does not exist."""
    directory = InMemoryTenantDirectory()
    tenant = directory.resolve(external_auth_id=CLERK_ORG, name="Coast Coffee")
    directory.set_tier(tenant.tenant_id, "operator")

    with pytest.raises(TierAlreadySetError) as refused:
        directory.set_tier(tenant.tenant_id, "command")

    assert refused.value.http_status == 409
    assert refused.value.detail is not None
    assert refused.value.detail["recorded_tier"] == "operator"
    assert refused.value.detail["requested_tier"] == "command"
    found = directory.get(tenant.tenant_id)
    assert found is not None and found.tier == "operator"


def test_renaming_the_organization_keeps_its_tier() -> None:
    directory = InMemoryTenantDirectory()
    tenant = directory.resolve(external_auth_id=CLERK_ORG, name="Coast Coffee")
    directory.set_tier(tenant.tenant_id, "strategist")

    renamed = directory.resolve(external_auth_id=CLERK_ORG, name="Coast Coffee Roasters")

    assert renamed.tier == "strategist"


def test_a_tier_cannot_be_set_for_a_tenant_that_was_never_registered() -> None:
    with pytest.raises(ToolError):
        InMemoryTenantDirectory().set_tier("ten_never_registered", "operator")


def test_the_passthrough_directory_holds_no_tier() -> None:
    """The filesystem layer has no table to keep a tier in, so it never reports one."""
    directory = PassthroughTenantDirectory()
    tenant = directory.resolve(external_auth_id=CLERK_ORG, name="Coast Coffee")

    accepted = directory.set_tier(tenant.tenant_id, "command")

    assert accepted.tier is None
    assert directory.resolve(external_auth_id=CLERK_ORG, name="Coast Coffee").tier is None


def test_the_recommended_tier_is_one_of_the_three() -> None:
    assert RECOMMENDED_TIER in TIER_NAMES


# --- Through the API ------------------------------------------------------------


NO_ORGANIZATION_TOKEN = "token.with.no.organization"


class _FakeVerifier:
    """A token verifier that reports one organization for any token but one.

    The one exception mirrors the real verifier: a token that carries no
    organization claim is refused before any tenant is resolved (ADR-0013).
    """

    def verify(self, token: str, request_path: str | None = None) -> VerifiedClaims:
        """Return fixed claims for any token except the organization-less one.

        Args:
            token: The bearer token; only :data:`NO_ORGANIZATION_TOKEN` is refused.
            request_path: The request path (ignored).

        Returns:
            Claims naming one signed-in person and their IdP organization.

        Raises:
            UnauthenticatedError: For the token that carries no organization.
        """
        if token == NO_ORGANIZATION_TOKEN:
            raise UnauthenticatedError("Sign in to continue.")
        return VerifiedClaims(
            user_id="usr_9f2c",
            organization_id=CLERK_ORG,
            email="sam@coastcoffee.example",
            business_name="Coast Coffee",
        )


def _seed_brand_dna(repo: Path, tenant_id: str) -> None:
    """Give a tenant a Brand DNA naming the segment the goal fixture targets.

    Creating a campaign refuses a segment the Brand DNA does not name, so a
    tenant minted mid-test needs one before it can own a campaign.

    Args:
        repo: The hermetic repository root.
        tenant_id: The platform tenant to write the Brand DNA for.
    """
    dna = repo / "tenants" / tenant_id / "dna.md"
    dna.parent.mkdir(parents=True, exist_ok=True)
    dna.write_text(
        "# Brand DNA — Coast Coffee\n\n"
        f"- **Primary segment(s):** {COMPLETE_GOAL_BODY['audience_segment']}\n",
        encoding="utf-8",
    )


def test_a_request_stores_its_documents_under_the_platform_tenant_not_the_org_id(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The end the whole indirection exists for: no Clerk id in a storage key."""
    monkeypatch.setenv("MARKETING_OS_ROOT", str(repo))
    import marketing_os.entrypoints.api.app as api

    api.get_settings.cache_clear()
    install_prototype_adapters(repo)
    api.app.dependency_overrides.clear()
    directory = InMemoryTenantDirectory()
    monkeypatch.setattr(api, "get_token_verifier", lambda: _FakeVerifier())
    monkeypatch.setattr(api, "get_tenant_directory", lambda: directory)
    _seed_brand_dna(repo, directory.resolve(external_auth_id=CLERK_ORG).tenant_id)

    with TestClient(api.app) as client:
        response = client.post(
            "/campaigns",
            json={**COMPLETE_GOAL_BODY, "name": "Spring"},
            headers={"Authorization": "Bearer any.token"},
        )
        assert response.status_code == 201
        assert client.get("/me", headers={"Authorization": "Bearer any.token"}).json() == {
            "user_id": "usr_9f2c",
            "email": "sam@coastcoffee.example",
            "business_name": "Coast Coffee",
            "tier": None,
        }

    tenant_id = directory.resolve(external_auth_id=CLERK_ORG).tenant_id
    assert (repo / "tenants" / tenant_id / "campaigns" / "spring" / "goal.md").is_file()
    assert not (repo / "tenants" / CLERK_ORG).exists()

    api.get_settings.cache_clear()
    clear_prototype_adapters()


# --- The tier, through the API --------------------------------------------------

AUTHORIZED = {"Authorization": "Bearer any.token"}


class _RememberingDirectory(InMemoryTenantDirectory):
    """A minting directory that also records which organizations it resolved.

    ``get`` is keyed by the platform id, which a test that wants to prove no
    tenant was minted for an organization does not have — so the directory
    says which organizations reached it instead.
    """

    def __init__(self) -> None:
        """Initialise the empty directory and its record of resolutions."""
        super().__init__()
        self.resolved: list[str] = []

    def resolve(self, *, external_auth_id: str, name: str | None = None) -> Tenant:
        """Resolve as the in-memory directory does, remembering the organization.

        Args:
            external_auth_id: The IdP's identifier for the business.
            name: The business's display name from the verified claim.

        Returns:
            The tenant that owns the business's data.
        """
        self.resolved.append(external_auth_id)
        return super().resolve(external_auth_id=external_auth_id, name=name)


@pytest.fixture
def tier_api(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[tuple[TestClient, _RememberingDirectory]]:
    """Yield an API client whose identity resolves through a minting directory.

    The default fixtures override the identity dependency wholesale, which is
    right for everything that happens *after* a tenant is known. The tier is
    different: it is the first call a new business makes, and the tenant it
    attaches to is minted by that very request. So these tests keep the real
    dependency and swap only what it depends on — a verifier that accepts a
    token, and a directory that remembers.

    Args:
        repo: The hermetic repository root fixture.
        monkeypatch: The pytest monkeypatch fixture.

    Yields:
        The entered client and the directory behind it.
    """
    monkeypatch.setenv("MARKETING_OS_ROOT", str(repo))
    import marketing_os.entrypoints.api.app as api

    api.get_settings.cache_clear()
    install_prototype_adapters(repo)
    api.app.dependency_overrides.clear()
    directory = _RememberingDirectory()
    monkeypatch.setattr(api, "get_token_verifier", lambda: _FakeVerifier())
    monkeypatch.setattr(api, "get_tenant_directory", lambda: directory)
    with TestClient(api.app) as client:
        yield client, directory
    api.get_settings.cache_clear()
    clear_prototype_adapters()


def test_a_business_that_has_never_set_a_tier_reports_none_over_the_api(
    tier_api: tuple[TestClient, _RememberingDirectory],
) -> None:
    client, _ = tier_api

    assert client.get("/me", headers=AUTHORIZED).json()["tier"] is None


def test_setting_a_tier_records_it_and_the_tenant_reads_it_back(
    tier_api: tuple[TestClient, _RememberingDirectory],
) -> None:
    client, directory = tier_api

    response = client.put("/tenant/tier", json={"tier": "command"}, headers=AUTHORIZED)

    assert response.status_code == 200, response.text
    assert response.json() == {"tier": "command"}
    assert client.get("/me", headers=AUTHORIZED).json()["tier"] == "command"
    assert directory.resolve(external_auth_id=CLERK_ORG).tier == "command"


def test_the_tier_call_is_the_first_call_a_new_business_makes(
    tier_api: tuple[TestClient, _RememberingDirectory],
) -> None:
    """There is no create-tenant endpoint: the tier call mints the tenant it attaches to."""
    client, directory = tier_api
    assert directory.resolved == []

    client.put("/tenant/tier", json={"tier": "strategist"}, headers=AUTHORIZED)

    assert directory.resolved == [CLERK_ORG]
    minted = directory.resolve(external_auth_id=CLERK_ORG)
    assert minted.tenant_id.startswith("ten_")
    assert minted.tier == "strategist"


def test_repeating_the_recorded_tier_succeeds_over_the_api(
    tier_api: tuple[TestClient, _RememberingDirectory],
) -> None:
    client, _ = tier_api
    client.put("/tenant/tier", json={"tier": "operator"}, headers=AUTHORIZED)

    again = client.put("/tenant/tier", json={"tier": "operator"}, headers=AUTHORIZED)

    assert again.status_code == 200
    assert again.json() == {"tier": "operator"}


def test_naming_a_different_tier_is_refused_with_409_and_a_typed_detail(
    tier_api: tuple[TestClient, _RememberingDirectory],
) -> None:
    client, _ = tier_api
    client.put("/tenant/tier", json={"tier": "operator"}, headers=AUTHORIZED)

    refused = client.put("/tenant/tier", json={"tier": "command"}, headers=AUTHORIZED)

    assert refused.status_code == 409
    body = refused.json()
    assert body["type"] == "tier_already_set"
    assert body["status"] == 409
    assert body["recorded_tier"] == "operator"
    assert body["requested_tier"] == "command"
    assert "operator" in body["message"]
    assert client.get("/me", headers=AUTHORIZED).json()["tier"] == "operator"


def test_an_unknown_tier_name_is_refused_with_422(
    tier_api: tuple[TestClient, _RememberingDirectory],
) -> None:
    client, _ = tier_api

    refused = client.put("/tenant/tier", json={"tier": "platinum"}, headers=AUTHORIZED)

    assert refused.status_code == 422
    body = refused.json()
    assert body["type"] == "validation"
    assert "platinum" in body["message"]
    assert client.get("/me", headers=AUTHORIZED).json()["tier"] is None


def test_a_caller_with_no_organization_claim_is_refused_with_401(
    tier_api: tuple[TestClient, _RememberingDirectory],
) -> None:
    """The redirect in the web app is a convenience; this refusal is the boundary."""
    client, directory = tier_api

    refused = client.put(
        "/tenant/tier",
        json={"tier": "operator"},
        headers={"Authorization": f"Bearer {NO_ORGANIZATION_TOKEN}"},
    )

    assert refused.status_code == 401
    assert refused.json()["type"] == "unauthenticated"
    assert directory.resolved == []


def test_an_unauthenticated_caller_cannot_set_a_tier(
    tier_api: tuple[TestClient, _RememberingDirectory],
) -> None:
    client, _ = tier_api

    assert client.put("/tenant/tier", json={"tier": "operator"}).status_code == 401

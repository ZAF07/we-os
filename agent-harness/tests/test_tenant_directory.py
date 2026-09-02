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

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from marketing_os.adapters.tenants import (
    InMemoryTenantDirectory,
    PassthroughTenantDirectory,
)
from marketing_os.errors import ToolError
from marketing_os.schemas import VerifiedClaims

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


# --- Through the API ------------------------------------------------------------


class _FakeVerifier:
    """A token verifier that accepts anything and reports one organization."""

    def verify(self, token: str) -> VerifiedClaims:
        """Return fixed claims for any token.

        Args:
            token: The bearer token (ignored).

        Returns:
            Claims naming one signed-in person and their IdP organization.
        """
        return VerifiedClaims(
            user_id="usr_9f2c",
            organization_id=CLERK_ORG,
            email="sam@coastcoffee.example",
            business_name="Coast Coffee",
        )


def test_a_request_stores_its_documents_under_the_platform_tenant_not_the_org_id(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The end the whole indirection exists for: no Clerk id in a storage key."""
    monkeypatch.setenv("MARKETING_OS_ROOT", str(repo))
    import marketing_os.entrypoints.api.app as api

    api.get_settings.cache_clear()
    api.reset_providers()
    api.app.dependency_overrides.clear()
    directory = InMemoryTenantDirectory()
    monkeypatch.setattr(api, "get_token_verifier", lambda: _FakeVerifier())
    monkeypatch.setattr(api, "get_tenant_directory", lambda: directory)

    with TestClient(api.app) as client:
        response = client.post(
            "/campaigns", json={"slug": "spring"}, headers={"Authorization": "Bearer any.token"}
        )
        assert response.status_code == 200
        assert client.get("/me", headers={"Authorization": "Bearer any.token"}).json() == {
            "user_id": "usr_9f2c",
            "email": "sam@coastcoffee.example",
            "business_name": "Coast Coffee",
        }

    tenant_id = directory.resolve(external_auth_id=CLERK_ORG).tenant_id
    assert (repo / "tenants" / tenant_id / "campaigns" / "spring" / "goal.md").is_file()
    assert not (repo / "tenants" / CLERK_ORG).exists()

    api.get_settings.cache_clear()
    api.reset_providers()

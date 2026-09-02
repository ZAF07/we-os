"""Tenant directory adapters — who owns the data an identity claim points at.

Implements the :class:`~marketing_os.ports.TenantDirectory` port (ADR-0014). The
identity provider names a business with its own identifier — Clerk issues an
Organization id such as ``org_3IlR...`` — and that identifier is a vendor
detail. Writing it into every document path, run row and checkpoint thread welds
the platform's partition key to one IdP account, so the directory translates it
once into a platform-owned ``tenant_id`` and records the pairing.

Two adapters, matching where documents live. The Postgres adapter (see
:mod:`marketing_os.adapters.postgres.tenants`) mints platform ids and stores the
external id beside the business name. The passthrough adapter is for the
filesystem layer, where a tenant *is* a directory name and there is no table to
mint an id in: it reports the external id as the tenant id, which is exactly the
pre-Postgres behaviour it preserves.
"""

from __future__ import annotations

from uuid import uuid4

from marketing_os.errors import ToolError
from marketing_os.schemas import Tenant

TENANT_ID_PREFIX = "ten_"


def new_tenant_id() -> str:
    """Mint a fresh platform tenant id.

    Returns:
        A ``ten_``-prefixed identifier owned by the platform, unrelated to any
        identity provider's naming.
    """
    return f"{TENANT_ID_PREFIX}{uuid4().hex}"


def display_name_for(external_auth_id: str, name: str | None) -> str:
    """Return the name to record for a business.

    Args:
        external_auth_id: The IdP's identifier for the business.
        name: The display name from the verified claim, if the token carried one.

    Returns:
        The claim's name when present, otherwise the external id, so a tenant is
        never nameless.
    """
    cleaned = (name or "").strip()
    return cleaned or external_auth_id


def validate_external_auth_id(external_auth_id: str) -> str:
    """Validate an identity provider's organization identifier.

    Args:
        external_auth_id: The identifier read from the verified organization claim.

    Returns:
        The identifier, stripped of surrounding whitespace.

    Raises:
        ToolError: If the identifier is empty.
    """
    cleaned = external_auth_id.strip()
    if not cleaned:
        raise ToolError("An identity claim carried no organization id.")
    return cleaned


class PassthroughTenantDirectory:
    """Reports the IdP's organization id as the tenant id, for the filesystem layer.

    Local development and the CLI resolve documents from ``tenants/<tenant>/``,
    where the directory name *is* the tenant id and there is no table to mint a
    platform id in. Minting one here would orphan every existing directory, so
    this adapter keeps the identifiers identical and defers the split to the
    Postgres deployment, where the external id gets its own column.
    """

    def resolve(self, *, external_auth_id: str, name: str | None = None) -> Tenant:
        """Return the tenant for an IdP organization, named after itself.

        Args:
            external_auth_id: The IdP's identifier for the business.
            name: The business's display name from the verified claim.

        Returns:
            A tenant whose ``tenant_id`` and ``external_auth_id`` are the same value.

        Raises:
            ToolError: If the external id is empty.
        """
        cleaned = validate_external_auth_id(external_auth_id)
        return Tenant(
            tenant_id=cleaned,
            name=display_name_for(cleaned, name),
            external_auth_id=cleaned,
        )

    def get(self, tenant_id: str) -> Tenant | None:
        """Return a tenant by its platform id.

        Args:
            tenant_id: The platform tenant id, which here is the external id.

        Returns:
            The tenant, or ``None`` when the id is empty.
        """
        cleaned = tenant_id.strip()
        if not cleaned:
            return None
        return Tenant(tenant_id=cleaned, name=cleaned, external_auth_id=cleaned)


class InMemoryTenantDirectory:
    """Mints platform tenant ids and holds the pairings in a dict.

    Behaves exactly as the Postgres directory does — a first sighting registers
    a tenant under a fresh platform id, a later one returns the same tenant and
    refreshes its recorded name — so tests can exercise the real translation
    without a database.
    """

    def __init__(self) -> None:
        """Initialise the empty directory."""
        self._by_external: dict[str, Tenant] = {}
        self._by_tenant: dict[str, Tenant] = {}

    def resolve(self, *, external_auth_id: str, name: str | None = None) -> Tenant:
        """Return the tenant for an IdP organization, registering it on first sight.

        Args:
            external_auth_id: The IdP's identifier for the business.
            name: The business's display name from the verified claim.

        Returns:
            The tenant that owns the business's data.

        Raises:
            ToolError: If the external id is empty.
        """
        cleaned = validate_external_auth_id(external_auth_id)
        existing = self._by_external.get(cleaned)
        tenant = Tenant(
            tenant_id=existing.tenant_id if existing else new_tenant_id(),
            name=display_name_for(cleaned, name),
            external_auth_id=cleaned,
        )
        self._by_external[cleaned] = tenant
        self._by_tenant[tenant.tenant_id] = tenant
        return tenant

    def get(self, tenant_id: str) -> Tenant | None:
        """Return a tenant by its platform id.

        Args:
            tenant_id: The platform tenant id.

        Returns:
            The tenant, or ``None`` when no tenant has that id.
        """
        return self._by_tenant.get(tenant_id)

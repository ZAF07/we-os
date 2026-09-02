"""Postgres :class:`~marketing_os.ports.TenantDirectory` — where the IdP pairing lives.

This is the adapter the user's note is about: the Clerk Organization id belongs
in a column of the ``tenants`` table, paired with the business's name and the
platform's own ``tenant_id``, rather than serving as the identifier that every
document path, run row and checkpoint thread is partitioned by (ADR-0014).
"""

from __future__ import annotations

from typing import Any

from marketing_os.adapters.tenants import (
    display_name_for,
    new_tenant_id,
    validate_external_auth_id,
)
from marketing_os.schemas import Tenant


class PostgresTenantDirectory:
    """Registers businesses in the ``tenants`` table and resolves them by IdP id."""

    def __init__(self, pool: Any) -> None:
        """Initialise the directory.

        Args:
            pool: A ``psycopg_pool.ConnectionPool``.
        """
        self._pool = pool

    def resolve(self, *, external_auth_id: str, name: str | None = None) -> Tenant:
        """Return the tenant for an IdP organization, registering it on first sight.

        A business's first authenticated request provisions its tenant; later
        requests find the same row, so renaming the organization in the IdP
        keeps the platform's copy current without disturbing ``tenant_id``.

        This runs on **every authenticated request**, so the common case — a
        known business whose name has not changed — is a read. Writing
        unconditionally would leave a dead row per request for the vacuum to
        clean up.

        Args:
            external_auth_id: The IdP's identifier for the business.
            name: The business's display name from the verified claim.

        Returns:
            The tenant that owns the business's data.

        Raises:
            ToolError: If the external id is empty.
        """
        cleaned = validate_external_auth_id(external_auth_id)
        display_name = display_name_for(cleaned, name)
        with self._pool.connection() as connection:
            row = connection.execute(
                "SELECT tenant_id, name, external_auth_id FROM tenants WHERE external_auth_id = %s",
                (cleaned,),
            ).fetchone()
            if row is not None and row[1] == display_name:
                return Tenant(tenant_id=row[0], name=row[1], external_auth_id=row[2])
            row = connection.execute(
                "INSERT INTO tenants (tenant_id, name, external_auth_id) VALUES (%s, %s, %s) "
                "ON CONFLICT (external_auth_id) DO UPDATE SET name = EXCLUDED.name "
                "RETURNING tenant_id, name, external_auth_id",
                (new_tenant_id(), display_name, cleaned),
            ).fetchone()
        return Tenant(tenant_id=row[0], name=row[1], external_auth_id=row[2])

    def get(self, tenant_id: str) -> Tenant | None:
        """Return a tenant by its platform id.

        Args:
            tenant_id: The platform tenant id.

        Returns:
            The tenant, or ``None`` when no tenant has that id.
        """
        with self._pool.connection() as connection:
            row = connection.execute(
                "SELECT tenant_id, name, external_auth_id FROM tenants WHERE tenant_id = %s",
                (tenant_id,),
            ).fetchone()
        if row is None:
            return None
        return Tenant(tenant_id=row[0], name=row[1], external_auth_id=row[2])

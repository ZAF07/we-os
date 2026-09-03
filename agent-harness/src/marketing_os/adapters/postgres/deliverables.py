"""Postgres :class:`~marketing_os.ports.DeliverableStore` — the production adapter.

Holds the same append-only version chain as the other adapters, so it passes the
same conformance suite and no caller can tell which store is behind the port
(ADR-0015). Two things it alone provides: a halted run's deliverable history
survives a restart, and the version number is assigned by the database rather
than by the process, so two writers cannot both believe they wrote version 3.

Every operation opens one transaction and sets the tenant for it before
querying, exactly as the document adapter does — the ``SET`` is what the
``deliverable_versions_tenant_isolation`` row-level-security policy checks, so a
query that somehow lost its ``tenant_id`` predicate still returns nothing across
tenants.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from marketing_os.adapters.deliverables import in_pipeline_order
from marketing_os.adapters.documents import validate_tenant_id
from marketing_os.adapters.postgres.schema import TENANT_SETTING
from marketing_os.schemas import DeliverableVersion

_COLUMNS = "stage_key, version, content, created_at, feedback, feedback_source, supersedes_version"


def _to_version(row: tuple[Any, ...]) -> DeliverableVersion:
    """Build a :class:`DeliverableVersion` from a selected row.

    Args:
        row: A row selected with :data:`_COLUMNS`, in that column order.

    Returns:
        The version the row records.
    """
    return DeliverableVersion(
        stage_key=str(row[0]),
        version=int(row[1]),
        content=str(row[2]),
        created_at=row[3].isoformat(),
        feedback=row[4],
        feedback_source=row[5],
        supersedes_version=row[6],
    )


class PostgresDeliverableStore:
    """Serves each tenant's deliverable version history from ``deliverable_versions``."""

    def __init__(self, pool: Any) -> None:
        """Initialise the store.

        Args:
            pool: A ``psycopg_pool.ConnectionPool`` whose connections belong to
                the application role (not a superuser, which bypasses RLS).
        """
        self._pool = pool

    @contextmanager
    def _scoped_to(self, tenant: str) -> Iterator[tuple[Any, str]]:
        """Open a transaction that may only touch one tenant's rows.

        Args:
            tenant: The tenant every statement in the transaction may touch.

        Yields:
            The open connection and the validated tenant id.

        Raises:
            ToolError: If the tenant id is malformed.
        """
        scoped_tenant = validate_tenant_id(tenant)
        with self._pool.connection() as connection:
            connection.execute("SELECT set_config(%s, %s, true)", (TENANT_SETTING, scoped_tenant))
            yield connection, scoped_tenant

    def append(
        self,
        tenant: str,
        slug: str,
        stage_key: str,
        content: str,
        *,
        feedback: str | None = None,
        feedback_source: str | None = None,
    ) -> DeliverableVersion:
        """Append a new version of a stage's deliverable.

        The number and the ``supersedes_version`` link are computed inside the
        insert, so concurrent appends serialise on the table's primary key
        rather than racing between a read and a write.

        Args:
            tenant: The tenant that owns the campaign.
            slug: The campaign slug.
            stage_key: The stage whose deliverable this is.
            content: The full deliverable markdown.
            feedback: The feedback that prompted this version, if any.
            feedback_source: ``human`` or ``reviewer``, if any.

        Returns:
            The stored version, carrying the number it was assigned.
        """
        with self._scoped_to(tenant) as (connection, scoped):
            row = connection.execute(
                "INSERT INTO deliverable_versions "
                "(tenant_id, slug, stage_key, version, content, feedback, feedback_source, "
                " supersedes_version) "
                "SELECT %s, %s, %s, next.number, %s, %s, %s, next.supersedes FROM ("
                "  SELECT COALESCE(MAX(version), 0) + 1 AS number, "
                "         NULLIF(COALESCE(MAX(version), 0), 0) AS supersedes "
                "  FROM deliverable_versions "
                "  WHERE tenant_id = %s AND slug = %s AND stage_key = %s"
                ") AS next "
                f"RETURNING {_COLUMNS}",
                (
                    scoped,
                    slug,
                    stage_key,
                    content,
                    feedback,
                    feedback_source,
                    scoped,
                    slug,
                    stage_key,
                ),
            ).fetchone()
        return _to_version(row)

    def latest(self, tenant: str, slug: str, stage_key: str) -> DeliverableVersion | None:
        """Return the newest version of a stage's deliverable.

        Args:
            tenant: The tenant that owns the campaign.
            slug: The campaign slug.
            stage_key: The stage whose deliverable to read.

        Returns:
            The newest version, or ``None`` when the stage has produced none.
        """
        with self._scoped_to(tenant) as (connection, scoped):
            row = connection.execute(
                f"SELECT {_COLUMNS} FROM deliverable_versions "
                "WHERE tenant_id = %s AND slug = %s AND stage_key = %s "
                "ORDER BY version DESC LIMIT 1",
                (scoped, slug, stage_key),
            ).fetchone()
        return _to_version(row) if row is not None else None

    def version(
        self, tenant: str, slug: str, stage_key: str, version: int
    ) -> DeliverableVersion | None:
        """Return one historical version of a stage's deliverable.

        Args:
            tenant: The tenant that owns the campaign.
            slug: The campaign slug.
            stage_key: The stage whose deliverable to read.
            version: The version number to read.

        Returns:
            That version, or ``None`` when it was never written.
        """
        with self._scoped_to(tenant) as (connection, scoped):
            row = connection.execute(
                f"SELECT {_COLUMNS} FROM deliverable_versions "
                "WHERE tenant_id = %s AND slug = %s AND stage_key = %s AND version = %s",
                (scoped, slug, stage_key, version),
            ).fetchone()
        return _to_version(row) if row is not None else None

    def history(self, tenant: str, slug: str, stage_key: str) -> list[DeliverableVersion]:
        """Return every version of a stage's deliverable, newest first.

        Args:
            tenant: The tenant that owns the campaign.
            slug: The campaign slug.
            stage_key: The stage whose history to read.

        Returns:
            The versions newest first, empty when the stage has produced none.
        """
        with self._scoped_to(tenant) as (connection, scoped):
            rows = connection.execute(
                f"SELECT {_COLUMNS} FROM deliverable_versions "
                "WHERE tenant_id = %s AND slug = %s AND stage_key = %s "
                "ORDER BY version DESC",
                (scoped, slug, stage_key),
            ).fetchall()
        return [_to_version(row) for row in rows]

    def stages(self, tenant: str, slug: str) -> list[str]:
        """Return the stage keys a campaign has produced a deliverable for.

        Args:
            tenant: The tenant that owns the campaign.
            slug: The campaign slug.

        Returns:
            The stage keys in mandatory pipeline order.
        """
        with self._scoped_to(tenant) as (connection, scoped):
            rows = connection.execute(
                "SELECT DISTINCT stage_key FROM deliverable_versions "
                "WHERE tenant_id = %s AND slug = %s",
                (scoped, slug),
            ).fetchall()
        return in_pipeline_order([str(row[0]) for row in rows])

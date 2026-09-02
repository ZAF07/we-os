"""Postgres :class:`~marketing_os.ports.DocumentStore` — the production adapter.

Addresses documents exactly as the filesystem adapter does — a tenant plus a
tenant-relative logical path — so it passes the same conformance suite and no
caller can tell which adapter is behind the port (ADR-0014).

Every operation opens one transaction, sets the tenant for that transaction, and
then queries. The ``SET`` is not a convenience: it is what the
``documents_tenant_isolation`` row-level-security policy checks, so a query that
somehow lost its ``tenant_id`` predicate still returns nothing across tenants.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from marketing_os.adapters.documents import normalise_document_path, validate_tenant_id
from marketing_os.adapters.postgres.schema import TENANT_SETTING
from marketing_os.errors import DocumentNotFoundError


class PostgresDocumentStore:
    """Serves each tenant's documents from the ``documents`` table.

    The tenant is set on the transaction before every statement, so row-level
    security scopes the query even if the SQL did not.
    """

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

        Setting ``marketing_os.tenant_id`` is what the row-level-security policy
        checks, and it is set here so there is no way to get a connection out of
        this store that has not been scoped. The validated tenant id is yielded
        alongside the connection so queries filter on exactly the value the
        policy was given — passing the raw argument instead would turn a padded
        tenant id into a confusing privilege error rather than a clear refusal.

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

    def read(self, tenant: str, path: str) -> str:
        """Return a document's text.

        Args:
            tenant: The tenant the document belongs to.
            path: The tenant-relative document path.

        Returns:
            The document content.

        Raises:
            DocumentNotFoundError: If no such document exists for the tenant.
        """
        document = normalise_document_path(path)
        with self._scoped_to(tenant) as (connection, scoped):
            row = connection.execute(
                "SELECT content FROM documents WHERE tenant_id = %s AND path = %s",
                (scoped, document),
            ).fetchone()
        if row is None:
            raise DocumentNotFoundError(f"Document not found: {path}")
        return str(row[0])

    def write(self, tenant: str, path: str, content: str) -> None:
        """Create or replace a document.

        Args:
            tenant: The tenant the document belongs to.
            path: The tenant-relative document path.
            content: The full document text.
        """
        document = normalise_document_path(path)
        with self._scoped_to(tenant) as (connection, scoped):
            connection.execute(
                "INSERT INTO documents (tenant_id, path, content) VALUES (%s, %s, %s) "
                "ON CONFLICT (tenant_id, path) "
                "DO UPDATE SET content = EXCLUDED.content, updated_at = now()",
                (scoped, document, content),
            )

    def exists(self, tenant: str, path: str) -> bool:
        """Return whether a document exists.

        Args:
            tenant: The tenant the document belongs to.
            path: The tenant-relative document path.

        Returns:
            ``True`` if the document exists for the tenant.
        """
        document = normalise_document_path(path)
        with self._scoped_to(tenant) as (connection, scoped):
            row = connection.execute(
                "SELECT 1 FROM documents WHERE tenant_id = %s AND path = %s",
                (scoped, document),
            ).fetchone()
        return row is not None

    def list(self, tenant: str, prefix: str) -> list[str]:
        """List the documents under a logical directory prefix.

        Args:
            tenant: The tenant whose documents are listed.
            prefix: The logical directory to list, for example ``campaigns/<slug>``.

        Returns:
            The sorted tenant-relative paths of every document under the prefix.
        """
        directory = normalise_document_path(prefix) + "/"
        with self._scoped_to(tenant) as (connection, scoped):
            rows = connection.execute(
                "SELECT path FROM documents "
                "WHERE tenant_id = %s AND starts_with(path, %s) ORDER BY path",
                (scoped, directory),
            ).fetchall()
        return [str(row[0]) for row in rows]

    def describe(self, tenant: str, path: str) -> str:
        """Return a human-readable database location for a document.

        Args:
            tenant: The tenant the document belongs to.
            path: The tenant-relative document path.

        Returns:
            A ``postgres:documents/<tenant>/<path>`` location string.
        """
        return f"postgres:documents/{tenant}/{normalise_document_path(path)}"

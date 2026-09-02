"""Postgres adapters, and the one object that opens and closes them together.

Importing this package pulls in ``psycopg``, which ships in the ``postgres``
extra rather than the base install — so nothing imports it at module scope. The
service reaches it only when a DSN is configured, and the fast test suite never
does.
"""

from __future__ import annotations

from typing import Any

from marketing_os.adapters.postgres.documents import PostgresDocumentStore
from marketing_os.adapters.postgres.runs import PostgresRunStore
from marketing_os.adapters.postgres.schema import ensure_schema, missing_tables
from marketing_os.adapters.postgres.tenants import PostgresTenantDirectory
from marketing_os.errors import ConfigError

__all__ = [
    "PostgresBackend",
    "PostgresDocumentStore",
    "PostgresRunStore",
    "PostgresTenantDirectory",
    "ensure_schema",
    "missing_tables",
]


class PostgresBackend:
    """Owns one connection pool and the adapters and checkpointer built over it.

    A single object because the four pieces share a lifetime: the pool must be
    open before any of them is used and closed after all of them are done. The
    service opens one in its lifespan and hands the parts out through its
    dependency providers.

    The document, tenant and run adapters use a **synchronous** pool because the
    :class:`~marketing_os.ports.DocumentStore` port is synchronous; the LangGraph
    checkpointer uses its own asynchronous connection because the graph is driven
    with ``astream`` (ADR-0009).
    """

    def __init__(self, dsn: str) -> None:
        """Initialise the backend without connecting.

        Args:
            dsn: The Postgres connection string.
        """
        self.dsn = dsn
        self._pool: Any = None
        self._checkpointer_context: Any = None
        self._checkpointer: Any = None

    async def open(self) -> None:
        """Connect, check the schema is provisioned, and prepare the checkpointer.

        The checkpointer's own tables are created by ``marketing-os init-db``
        too, so nothing here needs DDL rights.

        Raises:
            ConfigError: If the harness tables are absent. The service does not
                create them — it connects as a role without those rights — so it
                names the command that does rather than failing later on a query.
        """
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        from psycopg_pool import ConnectionPool

        self._pool = ConnectionPool(self.dsn, open=True)
        with self._pool.connection() as connection:
            absent = missing_tables(connection)
        if absent:
            raise ConfigError(
                f"Postgres is missing the harness tables: {', '.join(absent)}. "
                "Provision the database first: marketing-os init-db --dsn <admin dsn>."
            )

        self._checkpointer_context = AsyncPostgresSaver.from_conn_string(self.dsn)
        self._checkpointer = await self._checkpointer_context.__aenter__()

    async def close(self) -> None:
        """Release the checkpointer connection and the pool."""
        if self._checkpointer_context is not None:
            await self._checkpointer_context.__aexit__(None, None, None)
            self._checkpointer_context = None
            self._checkpointer = None
        if self._pool is not None:
            self._pool.close()
            self._pool = None

    @property
    def documents(self) -> PostgresDocumentStore:
        """Return the document store over this backend's pool."""
        return PostgresDocumentStore(self._pool)

    @property
    def tenants(self) -> PostgresTenantDirectory:
        """Return the tenant directory over this backend's pool."""
        return PostgresTenantDirectory(self._pool)

    @property
    def runs(self) -> PostgresRunStore:
        """Return the run store over this backend's pool."""
        return PostgresRunStore(self._pool)

    @property
    def checkpointer(self) -> Any:
        """Return the durable LangGraph checkpointer."""
        return self._checkpointer

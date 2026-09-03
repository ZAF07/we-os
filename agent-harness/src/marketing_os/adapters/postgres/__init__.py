"""Postgres adapters, and the one object that opens and closes them together.

Importing this package pulls in ``psycopg``, which ships in the ``postgres``
extra rather than the base install — so nothing imports it at module scope. The
service reaches it only when a DSN is configured, and the fast test suite never
does.
"""

from __future__ import annotations

from typing import Any

from marketing_os.adapters.postgres.deliverables import PostgresDeliverableStore
from marketing_os.adapters.postgres.documents import PostgresDocumentStore
from marketing_os.adapters.postgres.questionnaire import (
    PostgresAnswerStore,
    PostgresQuestionnaireStore,
)
from marketing_os.adapters.postgres.runs import PostgresRunStore
from marketing_os.adapters.postgres.schema import ensure_schema, missing_tables
from marketing_os.adapters.postgres.tenants import PostgresTenantDirectory
from marketing_os.adapters.postgres.usage import PostgresUsageLedger
from marketing_os.config import Settings
from marketing_os.errors import ConfigError

__all__ = [
    "PostgresAnswerStore",
    "PostgresBackend",
    "PostgresDeliverableStore",
    "PostgresDocumentStore",
    "PostgresQuestionnaireStore",
    "PostgresRunStore",
    "PostgresTenantDirectory",
    "PostgresUsageLedger",
    "ensure_schema",
    "missing_tables",
]


class PostgresBackend:
    """Owns one connection pool and the adapters and checkpointer built over it.

    A single object because the parts share a lifetime: the pool must be
    open before any of them is used and closed after all of them are done. The
    service opens one in its lifespan and hands the parts out through its
    dependency providers.

    The document, deliverable, tenant, run, questionnaire, answer and usage
    adapters use a **synchronous** pool because the
    :class:`~marketing_os.ports.DocumentStore` port is synchronous; the LangGraph
    checkpointer uses its own asynchronous connection because the graph is driven
    with ``astream`` (ADR-0009).
    """

    def __init__(self, dsn: str, settings: Settings | None = None) -> None:
        """Initialise the backend without connecting.

        Args:
            dsn: The Postgres connection string.
            settings: The harness settings the usage ledger prices calls and
                resolves the default allowance from; built from the environment
                when ``None``.
        """
        self.dsn = dsn
        self._settings = settings or Settings()
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
    def deliverables(self) -> PostgresDeliverableStore:
        """Return the deliverable version store over this backend's pool."""
        return PostgresDeliverableStore(self._pool)

    @property
    def tenants(self) -> PostgresTenantDirectory:
        """Return the tenant directory over this backend's pool."""
        return PostgresTenantDirectory(self._pool)

    @property
    def runs(self) -> PostgresRunStore:
        """Return the run store over this backend's pool."""
        return PostgresRunStore(self._pool)

    @property
    def questionnaires(self) -> PostgresQuestionnaireStore:
        """Return the questionnaire store over this backend's pool."""
        return PostgresQuestionnaireStore(self._pool)

    @property
    def answers(self) -> PostgresAnswerStore:
        """Return the Brand DNA answer store over this backend's pool."""
        return PostgresAnswerStore(self._pool)

    @property
    def usage(self) -> PostgresUsageLedger:
        """Return the usage ledger over this backend's pool."""
        return PostgresUsageLedger(self._pool, self._settings)

    @property
    def checkpointer(self) -> Any:
        """Return the durable LangGraph checkpointer."""
        return self._checkpointer

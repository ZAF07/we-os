"""Schema drift: what ``init-db`` repairs and what startup refuses to run on.

``CREATE TABLE IF NOT EXISTS`` is a no-op against a table that already exists
with an older column set, so a database provisioned before a column was added
passes a presence-only check and then fails on the first query that names the
column. These tests pin both halves of the fix: the expected shape is declared
data the fast suite can assert on, and the drift detection itself is proved
against a real Postgres.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest

from marketing_os.adapters.postgres.schema import (
    EXPECTED_COLUMNS,
    EXPECTED_INDEXES,
    SCHEMA_SQL,
    TABLES,
    ensure_schema,
    schema_drift,
)


@contextmanager
def _admin(dsn: str) -> Iterator[Any]:
    """Open an owning connection, since the application role may not alter tables.

    Args:
        dsn: The container's administrative connection string.

    Yields:
        An autocommit connection with rights to alter the schema.
    """
    import psycopg

    with psycopg.connect(dsn, autocommit=True) as connection:
        yield connection


def test_every_table_declares_the_columns_it_is_checked_for() -> None:
    """Assert the DDL parser found real columns for every table, not just some."""
    assert set(EXPECTED_COLUMNS) == set(TABLES)
    # Spot-check the shapes a mis-parse would quietly truncate: the first and
    # last column of a table, one carrying a multi-word type, and the columns
    # added by a later ALTER.
    assert EXPECTED_COLUMNS["documents"] == ("tenant_id", "path", "content", "updated_at")
    assert EXPECTED_COLUMNS["runs"] == (
        "run_id",
        "tenant_id",
        "user_id",
        "slug",
        "stage",
        "status",
        "started_at",
    )
    assert "credits" in EXPECTED_COLUMNS["tenants"]
    assert "sequence" in EXPECTED_COLUMNS["deliverable_versions"]
    for table, columns in EXPECTED_COLUMNS.items():
        assert columns, f"{table} declares no expected columns"
        assert not any(
            column.upper() in {"PRIMARY", "UNIQUE", "CONSTRAINT"} for column in columns
        ), f"{table} parsed a table constraint as a column: {columns}"


def test_every_declared_index_is_checked_for() -> None:
    """Assert the DDL parser found every index, including the multi-line one."""
    assert set(EXPECTED_INDEXES) == {
        "runs_one_active_per_campaign",
        "runs_by_status",
        "usage_ledger_by_tenant",
        "usage_ledger_by_campaign",
    }
    assert set(EXPECTED_INDEXES.values()) <= set(TABLES)


def test_columns_added_after_a_table_shipped_are_repaired_not_only_created() -> None:
    # A column introduced after the table existed somewhere must carry an
    # explicit ALTER, or `init-db` reports success without adding it.
    for table, column in (("runs", "user_id"), ("tenants", "credits")):
        assert f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column}" in SCHEMA_SQL, (
            f"{table}.{column} is only created inside CREATE TABLE IF NOT EXISTS"
        )


@pytest.mark.slow
def test_a_database_missing_a_column_is_reported_as_stale(
    postgres_dsn: str, postgres_superuser_dsn: str
) -> None:
    # This is the exact shape of the reported defect: a `runs` table provisioned
    # before `user_id` existed, which the presence-only check waved through and
    # which then failed at the first query naming the column.
    with _admin(postgres_superuser_dsn) as admin:
        admin.execute("ALTER TABLE runs DROP COLUMN user_id")
        try:
            drift = schema_drift(admin)
            assert any("runs.user_id" in item for item in drift), drift
        finally:
            ensure_schema(admin)


@pytest.mark.slow
def test_ensure_schema_repairs_a_dropped_column(
    postgres_dsn: str, postgres_superuser_dsn: str
) -> None:
    with _admin(postgres_superuser_dsn) as admin:
        admin.execute("ALTER TABLE runs DROP COLUMN user_id")
        assert schema_drift(admin)
        ensure_schema(admin)
        assert schema_drift(admin) == []


@pytest.mark.slow
def test_a_missing_index_is_reported_as_stale(
    postgres_dsn: str, postgres_superuser_dsn: str
) -> None:
    with _admin(postgres_superuser_dsn) as admin:
        admin.execute("DROP INDEX runs_by_status")
        try:
            assert any("runs_by_status" in item for item in schema_drift(admin))
        finally:
            ensure_schema(admin)


@pytest.mark.slow
def test_a_provisioned_database_reports_no_drift(postgres_pool: Any) -> None:
    with postgres_pool.connection() as connection:
        assert schema_drift(connection) == []


@pytest.mark.slow
def test_a_database_with_the_old_allowance_column_is_renamed_to_credits(
    postgres_dsn: str, postgres_superuser_dsn: str
) -> None:
    """Assert a database provisioned before the rename is carried across.

    Such a database carries ``tenants.allowance``. The rename must bring the
    column *and the values on it* over, so a design partner's raised ceiling
    survives the deploy rather than silently reverting to the platform default.

    Args:
        postgres_dsn: The application-role connection string.
        postgres_superuser_dsn: The administrative connection string.
    """
    with _admin(postgres_superuser_dsn) as admin:
        admin.execute("ALTER TABLE tenants RENAME COLUMN credits TO allowance")
        admin.execute(
            "INSERT INTO tenants (tenant_id, name, external_auth_id, allowance)"
            " VALUES ('renamed', 'Renamed', 'auth-renamed', 99)"
        )
        try:
            ensure_schema(admin)
            assert schema_drift(admin) == []
            assert _columns_of(admin, "tenants") >= {"credits"}
            assert "allowance" not in _columns_of(admin, "tenants")
            carried = admin.execute(
                "SELECT credits FROM tenants WHERE tenant_id = 'renamed'"
            ).fetchone()
            assert carried is not None and float(carried[0]) == 99.0
        finally:
            admin.execute("DELETE FROM tenants WHERE tenant_id = 'renamed'")
            ensure_schema(admin)


@pytest.mark.slow
def test_running_the_rename_twice_is_harmless(postgres_superuser_dsn: str) -> None:
    """Assert the rename is idempotent, like the rest of the schema module.

    The second start of a service already on the new column must not re-run the
    rename, and a fresh database has no old column to rename at all.

    Args:
        postgres_superuser_dsn: The administrative connection string.
    """
    with _admin(postgres_superuser_dsn) as admin:
        ensure_schema(admin)
        ensure_schema(admin)
        assert schema_drift(admin) == []
        assert "allowance" not in _columns_of(admin, "tenants")


def _columns_of(connection: Any, table: str) -> set[str]:
    """Return the column names a table actually has in the database.

    Args:
        connection: An open psycopg connection.
        table: The table to inspect.

    Returns:
        Every column name on the table.
    """
    rows = connection.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
        (table,),
    ).fetchall()
    return {row[0] for row in rows}

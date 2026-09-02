"""The Postgres schema the harness owns, and how tenant isolation is enforced in it.

Three tables (ADR-0014):

``tenants``
    The pairing the identity provider cannot be trusted to hold. ``tenant_id``
    is minted by the platform and is what every other table partitions on;
    ``external_auth_id`` is the IdP's own identifier for the business — for Clerk,
    the Organization id — kept in one column so swapping IdP, re-linking an
    organization, or renaming a business touches one row rather than every
    document path and checkpoint thread.

``documents``
    The markdown the pipeline reads and writes, addressed exactly as the
    filesystem adapter addresses it: a tenant plus a tenant-relative logical
    path. There is deliberately **no foreign key** to ``tenants`` — the
    conformance suite writes documents for bare tenant ids, and the store's
    contract is "documents are scoped by whatever tenant id you give", not
    "documents require a registered tenant".

``runs``
    The one-active-run-per-campaign claim, who holds it, and each run's
    lifecycle status. The partial unique index is what makes the claim real: a
    second ``running`` row for the same ``(tenant_id, slug)`` cannot exist, so
    the guard is Postgres's to enforce rather than a check some new call site
    can forget. ``user_id`` records the person driving the campaign, since one
    campaign is run by one person at a time.

**Creating the schema is an operator step, not a boot step.** The service
connects as an ordinary role that deliberately has no rights to create tables —
handing the runtime DDL privileges to save one deployment command is how an
application ends up owning its own security boundary. ``marketing-os init-db``
provisions with an administrative DSN; the service only checks the tables are
there and says what to run if they are not.

**Row-level security backstops the ``documents`` scoping.** Every read and write
runs inside a transaction that has set ``marketing_os.tenant_id``, and the policy
admits only rows matching it — so even a query that forgot its ``WHERE
tenant_id`` clause returns nothing across tenants. ``FORCE ROW LEVEL SECURITY``
extends the policy to the table's owner. It does **not** extend to superusers or
roles with ``BYPASSRLS``: the application must connect as an ordinary role, which
is what :func:`grant_application_role_sql` provisions.

RLS is applied to ``documents`` and not to ``runs`` because resolving runs left
over from a crash is a cross-tenant maintenance sweep with no tenant in scope;
the runs queries carry an explicit ``tenant_id`` predicate on every
tenant-facing path instead.
"""

from __future__ import annotations

from typing import Any

TENANT_SETTING = "marketing_os.tenant_id"

SCHEMA_SQL = f"""
CREATE TABLE IF NOT EXISTS tenants (
    tenant_id        text PRIMARY KEY,
    name             text NOT NULL,
    external_auth_id text NOT NULL UNIQUE,
    created_at       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS documents (
    tenant_id  text NOT NULL,
    path       text NOT NULL,
    content    text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, path)
);

ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS documents_tenant_isolation ON documents;
CREATE POLICY documents_tenant_isolation ON documents
    USING (tenant_id = current_setting('{TENANT_SETTING}', true))
    WITH CHECK (tenant_id = current_setting('{TENANT_SETTING}', true));

CREATE TABLE IF NOT EXISTS runs (
    run_id     text PRIMARY KEY,
    tenant_id  text NOT NULL,
    user_id    text NOT NULL DEFAULT '',
    slug       text NOT NULL,
    stage      text,
    status     text NOT NULL,
    started_at double precision NOT NULL DEFAULT 0
);

CREATE UNIQUE INDEX IF NOT EXISTS runs_one_active_per_campaign
    ON runs (tenant_id, slug) WHERE status = 'running';
CREATE INDEX IF NOT EXISTS runs_by_status ON runs (status);
"""


TABLES = ("tenants", "documents", "runs")


def ensure_schema(connection: Any) -> None:
    """Create the harness tables, indexes and policies if they are absent.

    Idempotent, so it is safe to re-run. Needs an administrative connection —
    the application's own role has no rights to create objects.

    Args:
        connection: An open psycopg connection with rights to create objects.
    """
    connection.execute(SCHEMA_SQL)


def missing_tables(connection: Any) -> list[str]:
    """Return the harness tables the database does not have.

    Args:
        connection: An open psycopg connection.

    Returns:
        The names of any missing tables, so the service can say what to run
        rather than failing on the first query with a confusing error.
    """
    rows = connection.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_name = ANY(%s)",
        (list(TABLES),),
    ).fetchall()
    present = {row[0] for row in rows}
    return [name for name in TABLES if name not in present]


def grant_application_role_sql(role: str) -> str:
    """Return the SQL granting a non-superuser role the access the harness needs.

    Row-level security does not constrain superusers, so the application must
    connect as an ordinary role for the ``documents`` policy to mean anything.
    The grant covers every table in the schema — the harness's three plus the
    checkpointer's own — and deliberately stops short of any right to create,
    alter or drop.

    Run it **after** the checkpointer's tables exist, or its tables are missed.

    Args:
        role: The database role the application connects as.

    Returns:
        The DDL granting the role table access, as one script.
    """
    return f"""
    GRANT USAGE ON SCHEMA public TO {role};
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {role};
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {role};
    """

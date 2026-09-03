# `init-db` reports success on an out-of-date database, which then fails at query time

Status: needs-triage
Type: bug

## Parent

`.scratch/saas-foundation/issues/archive/05-postgres-adapter-durable-checkpointer-shared-registry.md` — this is a defect in that implementation.
[ADR-0014](../../../docs/adr/0014-postgres-system-of-record-and-split-governance.md)

## What's wrong

`SCHEMA_SQL` is built entirely from `CREATE TABLE IF NOT EXISTS`
([schema.py:88-158](../../../agent-harness/src/marketing_os/adapters/postgres/schema.py#L88-L158)).
When a table already exists with an older column set, the statement is a no-op —
no column is added, and no error is raised. `ensure_schema` then returns cleanly
and `init-db` prints:

```
Created the tenants, documents and runs tables, indexes and RLS policy.
Created the LangGraph checkpointer tables.
Granted table access to 'marketing_os_app'.
```

Nothing was created. The startup check does not catch it either: `missing_tables`
([schema.py:191](../../../agent-harness/src/marketing_os/adapters/postgres/schema.py#L191))
queries `information_schema.tables` for table **presence** only and never
inspects columns, so an out-of-date table passes.

The failure therefore surfaces at the first query against the missing column, as
an unhandled psycopg error during application startup:

```
psycopg.errors.UndefinedColumn: column "user_id" does not exist
LINE 1: ...E status = 'running' RETURNING run_id, tenant_id, user_id, s...
ERROR:    Application startup failed. Exiting.
```

This is the opposite of what `missing_tables` was written for — its docstring
says it exists "so the service can say what to run rather than failing on the
first query with a confusing error."

## Reproduction

Hit on 2026-09-02 against a `docker compose` Postgres left over from an earlier
run, on a build predating the `runs.user_id` column:

1. Have a database whose `runs` table predates `user_id`.
2. `uv run marketing-os init-db --dsn <admin dsn> --app-role marketing_os_app`
   → reports success; `\d runs` still shows no `user_id`.
3. Start the API → `UndefinedColumn`, startup fails.
4. `docker compose down -v` and re-init → works.

## Why this is worth fixing now rather than later

The schema has kept moving since. On current `main` it carries a
`deliverable_versions` table and a changed `runs_one_active_per_campaign` index
that earlier databases do not have. `deliverable_versions` is at least covered by
the `missing_tables` presence check; **column and index drift is not caught at
all**. Anyone with a database from before those changes gets a success message
followed by a runtime error, and the only documented recovery
(`make db-down`, which is `docker compose down -v`) destroys the data.

## Notes for whoever picks this up

The fix could go several ways, and the choice is a real one:

- Extend `missing_tables` into a schema check that also compares columns and
  indexes, and refuse to start with a message naming what is stale.
- Introduce actual migrations, which is the honest answer once there is data
  worth preserving but is a bigger commitment.
- At minimum, stop `init-db` claiming it created things it did not.

Worth deciding before there is production data, not after.

## Evidence

- [schema.py:88-158](../../../agent-harness/src/marketing_os/adapters/postgres/schema.py#L88-L158) — `CREATE TABLE IF NOT EXISTS` throughout.
- [schema.py:179](../../../agent-harness/src/marketing_os/adapters/postgres/schema.py#L179) — `ensure_schema`, documented as "idempotent, safe to re-run".
- [schema.py:191](../../../agent-harness/src/marketing_os/adapters/postgres/schema.py#L191) — `missing_tables`, presence-only.

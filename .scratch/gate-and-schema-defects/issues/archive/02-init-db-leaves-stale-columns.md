# `init-db` reports success on an out-of-date database, which then fails at query time

Status: completed
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

## Comments

**2026-09-03.** Fixed, taking the first of the three offered directions plus the
"at minimum" one.

Decisions settled, per the "Notes for whoever picks this up":

- **`missing_tables` is extended into `schema_drift`**, which compares columns
  and indexes as well as table presence and returns what is stale. Startup now
  refuses with that list rather than failing on the first query.
- **`init-db` no longer claims work it did not do.** All three of its report
  lines were dishonest on an already-provisioned database; they now read "are up
  to date" / "has table access". If drift remains after `ensure_schema`, it says
  so, lists what is missing, and exits 1.
- **Columns added after their table shipped now carry an explicit ALTER**, so
  `init-db` repairs them in place instead of no-opping. `runs.user_id` — the
  column from this report — is the case that was missing one.
- **Migrations were not introduced.** That is the honest answer once there is
  data worth preserving, and remains the right call to make before production
  data exists — but it is a bigger commitment than this defect needs, and
  drift is now caught rather than silent.

The expected shape is parsed out of `SCHEMA_SQL` itself (`EXPECTED_COLUMNS`,
`EXPECTED_INDEXES`), so a column added to the DDL is checked for from the moment
it is written, with nothing separate to remember to update.

### Accepted limitations

- **Index definitions are matched by name, not predicate.** An old index with the
  same name and a different `WHERE` clause reports no drift. `ensure_schema`
  repairs this case anyway via the `DROP INDEX IF EXISTS` that precedes the
  create, so the fix works — but the startup check would pass a stale definition.
- **The checkpointer's own tables are outside `TABLES`** and so are not inspected.
  They are LangGraph's schema, not ours.

### Verification

Against the containerised Postgres, reproducing this report's exact scenario:

```
$ ALTER TABLE runs DROP COLUMN user_id      # a database predating the column
$ uv run marketing-os init-db --dsn <dsn> --app-role marketing_os_app
The tenants, documents and runs tables, indexes and RLS policy are up to date.
$ \d runs  →  user_id present again          # repaired, not falsely reported
```

And a column with no repair ALTER, which must be refused rather than crash:

```
$ ALTER TABLE documents DROP COLUMN updated_at
$ PostgresBackend.open()
ConfigError: Postgres is out of date. Missing: column documents.updated_at.
Bring the database up to date: marketing-os init-db --dsn <admin dsn>.
```

That replaces the `psycopg.errors.UndefinedColumn` / "Application startup failed"
this report opened with.

Tests: `test_schema_drift.py` — six, four against a real Postgres
(`test_a_database_missing_a_column_is_reported_as_stale` drops `runs.user_id`
exactly as this report describes).

## Completion

- Completed: 2026-09-03
- Commit: 6636cfe

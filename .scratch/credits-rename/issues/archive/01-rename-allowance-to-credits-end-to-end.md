# 01 — Rename allowance to credits, end to end

Status: completed
Type: task

## Parent

[ADR-0020](../../../docs/adr/0020-usage-ledger-and-enforced-quota.md) (2026-09-08 amendment) · [PRD: We-OS Landing and Pricing](../../landing-and-pricing/PRD.md) (which deferred this rename) · **Credits** in [CONTEXT.md](../../../CONTEXT.md)

## What to build

The glossary now says **credits** for what a business may spend on generation. The code still says `allowance` everywhere: the Postgres column on the tenants table, the platform-default setting and its `MARKETING_OS_ALLOWANCE` env var, the usage report field, the quota error's field and 402 detail key, the ledger port's set method, the adapters, the `/usage` response and 402 body in the OpenAPI contract, the web engine client type, Home's projections, the refusal message, run progress, and the tests behind all of it.

Rename all of it to `credits` in one change, engine and web together, because the API field is the seam between them and renaming one side alone breaks Home. Behaviour is identical afterwards: the same numbers, the same check-then-charge ordering, the same 402. Only the name moves.

The column rename must be idempotent like the rest of the schema module: renaming `tenants.allowance` to `tenants.credits` only when the old column exists, and a no-op on a fresh database or a second start. The schema-drift test expects the new column and not the old. The env var becomes `MARKETING_OS_CREDITS`; the old name is not read.

User-facing strings say "credits" ("Your credits are used up. Work resumes when they renew."). Docstrings and comments follow the glossary: quota is the enforcement, credits are the amount.

Sequencing: Landing issue 01 changes Home's visible "Allowance" label to "Credits" in copy only. Do this rename after that lands, or coordinate on the same branch, to avoid a conflict on the same lines.

## Acceptance criteria

- [x] `grep -ri allowance` over engine source, engine tests, the OpenAPI contract, web source, and web tests returns nothing except the ADR history and the glossary's "avoid" note.
- [x] The tenants table has a `credits` column and no `allowance` column after a start against a database that had the old column, and after a start against a fresh database; starting twice is harmless.
- [x] `MARKETING_OS_CREDITS` sets the platform default; a tenant override still wins.
- [x] `/usage` returns `credits` where it returned `allowance`; the 402 detail carries `credits`; the OpenAPI contract and its example match.
- [x] Home renders the credits card and stat tile from the renamed field; a quota refusal reads "credits" in the app.
- [x] `uv run ruff check .`, `uv run ruff format --check`, `uv run mypy src`, and `uv run pytest` pass in the engine; `pnpm typecheck`, `pnpm lint`, `pnpm format:check`, `pnpm test:unit`, and `pnpm test` pass in web; the change is checked in the running app.

## Blocked by

None - can start immediately (but see sequencing note above)

## Completion

- Completed: 2026-09-08
- Commit: `3992000` (implementation), `dbe76ff` (code-review fixes), merged to main as `1ebf441`

### Evidence

- **Criterion 1** — `grep -ri allowance` is clean across engine source, engine tests, the contract, web source and web tests, *except* the guarded migration in `adapters/postgres/schema.py` and the two tests exercising it in `tests/test_schema_drift.py`. Those name the old column because criterion 2 requires the rename to find it; the criteria are in tension and the migration requirement is the more specific one. `CONTEXT.md` and ADR-0020 were also updated (they were stale, not exempt).
- **Criterion 2** — guarded `DO $$ … RENAME COLUMN allowance TO credits`, conditional on old-exists AND new-not-exists, then `ADD COLUMN IF NOT EXISTS credits`. Pinned by `test_a_database_with_the_old_allowance_column_is_renamed_to_credits` (asserts the *value* carries across, not just the column) and `test_running_the_rename_twice_is_harmless`. Both proved red before the migration existed. Also verified live: a real Postgres seeded with `allowance = 7` came out as `credits = 7` after `init-db`, unchanged after a second run.
- **Criterion 3** — `config.py` reads `MARKETING_OS_CREDITS`; the old name is not read anywhere. Verified live: platform default 3.0 from the env var, tenant override of 7.0 winning over it.
- **Criterion 4** — `/usage` returns `credits` (`app.py:634`); the 402 detail carries `credits` (`errors.py:215`). The contract example was cost-shaped (`used: 4.2`) and contradicted its own "whole credits" prose; fixed in `dbe76ff`.
- **Criterion 5** — `CreditsCard` and the "Credits used" stat tile read `usage.credits`; the refusal message reads "Your credits are used up. Work resumes when they renew."
- **Criterion 6** — engine `ruff check`, `ruff format --check`, `mypy src` all pass; `make test-postgres` 682 passed. Web `pnpm typecheck`, `lint`, `format:check`, `test:unit` (69) all pass. `pnpm test` (Playwright) run via `make test-e2e`: **45 passed, 3 failed**, and separately **47 passed, 1 failed** at `--workers=1`. The failures are pre-existing suite flakiness, not this change — pre-change `main` (`345ebbb`) fails the same count with a *different* set of specs, and every failing test passed on rerun. Filed as [e2e-suite-flake 01](../../../e2e-suite-flake/issues/01-campaign-creating-specs-fail-under-parallel-workers.md). The one spec line this change touches (`home.spec.ts:18`, "Allowance" → "Credits") passed in all four runs. The change was also checked in the running app against a real Postgres.

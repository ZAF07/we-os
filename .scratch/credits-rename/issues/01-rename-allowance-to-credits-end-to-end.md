# 01 — Rename allowance to credits, end to end

Status: ready-for-agent
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

- [ ] `grep -ri allowance` over engine source, engine tests, the OpenAPI contract, web source, and web tests returns nothing except the ADR history and the glossary's "avoid" note.
- [ ] The tenants table has a `credits` column and no `allowance` column after a start against a database that had the old column, and after a start against a fresh database; starting twice is harmless.
- [ ] `MARKETING_OS_CREDITS` sets the platform default; a tenant override still wins.
- [ ] `/usage` returns `credits` where it returned `allowance`; the 402 detail carries `credits`; the OpenAPI contract and its example match.
- [ ] Home renders the credits card and stat tile from the renamed field; a quota refusal reads "credits" in the app.
- [ ] `uv run ruff check .`, `uv run ruff format --check`, `uv run mypy src`, and `uv run pytest` pass in the engine; `pnpm typecheck`, `pnpm lint`, `pnpm format:check`, `pnpm test:unit`, and `pnpm test` pass in web; the change is checked in the running app.

## Blocked by

None - can start immediately (but see sequencing note above)

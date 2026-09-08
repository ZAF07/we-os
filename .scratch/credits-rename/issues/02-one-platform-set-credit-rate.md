# 02 — One platform-set credit rate

Status: ready-for-agent
Type: task

## Parent

[ADR-0020](../../../docs/adr/0020-usage-ledger-and-enforced-quota.md) (2026-09-08 amendment) · **Credits** and **Tier** in [CONTEXT.md](../../../CONTEXT.md)

## What to build

After issue 01 the engine calls the number "credits", but the number is still real model cost: one unit of cost equals one credit. The tiers say Operator gets 6,000 credits for USD 59 a month, so a credit cannot be a dollar of cost. There has to be an exchange rate, and the glossary promises it lives in one place.

Add one setting, `MARKETING_OS_CREDIT_RATE`: how many credits one unit of recorded cost burns. Default 1, so nothing changes until it is set. The usage ledger keeps recording real cost, unchanged, so it stays the unit-economics dataset. Credits are derived from cost at the rate in exactly two places: the usage report (used, credits, remaining) and the quota check before a billable call. A tenant's credits, platform default or override, are stored and compared in credits; the ledger's recorded cost is multiplied by the rate to compare against them.

Example the docstrings can use: rate 100 means a call that cost 0.03 burns 3 credits.

Rounding: report credits as whole numbers (round half up) in the usage report; the quota check compares the unrounded value so a tenant is not refused a hair early or late because of display rounding.

The OpenAPI contract's `/usage` description says credits are derived from recorded cost at a platform rate. Home needs no change beyond formatting credits as whole numbers rather than to two decimals.

## Acceptance criteria

- [ ] With the rate unset, every existing engine and web test passes unchanged: behaviour is identical to issue 01.
- [ ] With rate 100 and a tenant granted 300 credits, three calls costing 1.00 each are allowed and a fourth is refused with 402; the usage report shows 300 used, 300 credits, 0 remaining, exhausted true.
- [ ] The ledger rows for those calls still record cost 1.00 each, not credits.
- [ ] The rate is read in one place (config) and applied in the usage adapter's report and check paths only; billing's check-then-charge ordering is untouched.
- [ ] The usage report and Home show credits as whole numbers.
- [ ] `uv run ruff check .`, `uv run ruff format --check`, `uv run mypy src`, and `uv run pytest` pass in the engine; `pnpm typecheck`, `pnpm lint`, `pnpm format:check`, `pnpm test:unit`, and `pnpm test` pass in web; the change is checked in the running app.

## Blocked by

- [01 — Rename allowance to credits, end to end](01-rename-allowance-to-credits-end-to-end.md)

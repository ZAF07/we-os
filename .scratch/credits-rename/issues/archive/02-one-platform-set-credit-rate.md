# 02 — One platform-set credit rate

Status: completed
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

- [x] With the rate unset, every existing engine and web test passes unchanged: behaviour is identical to issue 01.
- [x] With rate 100 and a tenant granted 300 credits, three calls costing 1.00 each are allowed and a fourth is refused with 402; the usage report shows 300 used, 300 credits, 0 remaining, exhausted true.
- [x] The ledger rows for those calls still record cost 1.00 each, not credits.
- [x] The rate is read in one place (config) and applied in the usage adapter's report and check paths only; billing's check-then-charge ordering is untouched.
- [x] The usage report and Home show credits as whole numbers.
- [x] `uv run ruff check .`, `uv run ruff format --check`, `uv run mypy src`, and `uv run pytest` pass in the engine; `pnpm typecheck`, `pnpm lint`, `pnpm format:check`, `pnpm test:unit`, and `pnpm test` pass in web; the change is checked in the running app.

## Blocked by

- [01 — Rename allowance to credits, end to end](01-rename-allowance-to-credits-end-to-end.md)

## Completion

- Completed: 2026-09-08
- Commit: `903bfa6` (implementation), `dbe76ff` (code-review fixes), merged to main as `1ebf441`

### Evidence

- **Criterion 1** — `credit_rate` defaults to 1, so cost and credits stay one-to-one. Whole suite green with the rate unset: engine 682 passed, web 69 passed. Pinned explicitly by `test_with_no_rate_set_one_unit_of_cost_is_one_credit`.
- **Criterion 2** — `test_a_tenant_is_refused_once_their_credits_are_spent_at_the_rate` (both ledger adapters) and `test_credits_are_spent_at_the_platform_rate_and_then_refused` (through the API). Verified live against a real Postgres: three calls costing 1.00 allowed at rate 100 with 300 credits, report showed `used 300, credits 300, remaining 0, exhausted True`, fourth call refused with 402.
- **Criterion 3** — `build_entry` still records `cost_of(...)`, untouched by the rate. Pinned by `test_the_ledger_still_records_real_cost_not_credits`; live run confirmed the three stored rows each held cost `1.0`.
- **Criterion 4** — the rate is read only in `config.py` (`MARKETING_OS_CREDIT_RATE`) and applied only in `credits_of`, called only from `build_consumption`, which both ledger adapters now go through. `billing.py` is unchanged in this commit, so check-then-charge ordering is untouched.
- **Criterion 5** — `whole_credits` rounds half up via `Decimal` at the API boundary only; `refuse_when_exhausted` compares the unrounded `Consumption.used`. Home formats with `Math.round`. Pinned by `test_credits_are_shown_rounded_half_up` (parametrised, including the 2.5 → 3 case banker's rounding would get wrong) and `test_the_usage_report_shows_credits_as_whole_numbers`.
- **Criterion 6** — same as issue 01: all engine and web gates pass, and `pnpm test` (Playwright) was run via `make test-e2e` — 45 passed / 3 failed, and 47 passed / 1 failed at `--workers=1`. Those failures are pre-existing suite flakiness reproduced on pre-change `main`, filed as [e2e-suite-flake 01](../../../e2e-suite-flake/issues/01-campaign-creating-specs-fail-under-parallel-workers.md). Verified in the running app against a real Postgres.

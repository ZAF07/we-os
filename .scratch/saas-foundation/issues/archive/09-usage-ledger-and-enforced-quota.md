# 09 — Usage ledger and enforced quota

Status: completed
Type: task

## Parent

[PRD: we-OS SaaS foundation](../PRD.md) · [ADR-0020](../../../docs/adr/0020-usage-ledger-and-enforced-quota.md)

## What to build

Every billable model call is recorded against its tenant with its cost, and the tenant's allowance is checked **before** the call rather than after.

Today the only cost telemetry is per-run token usage folded into the run result — neither persisted per tenant nor capped — and the QA iteration limit bounds only the _automated_ revision loop. Nothing bounds human revision, which slice 07 just introduced. With image generation arriving in a later PRD, one business clicking "try again" repeatedly costs real money with no ceiling and no record.

Exceeding the allowance raises a typed quota failure, surfaced as **402**, so starting a run and revising a stage both carry that outcome in their contract. An endpoint that cannot fail with "quota exceeded" is an endpoint whose contract has to change later — which is why this is built while pre-revenue rather than after.

Hard caps sit alongside the ledger: a maximum number of revisions per deliverable, and runs per campaign.

How the allowance is _presented_ — credits, fair use on a flat plan, metered billing — is deliberately out of scope. The mechanism is not.

The ledger doubles as the unit-economics dataset: what a campaign, a revision, and a business actually cost.

End-to-end behaviour: run campaigns until the allowance is exhausted, see work refused with a clear message rather than a generic error, and see consumption reflected in the interface throughout.

## Acceptance criteria

- [x] Every billable model call is recorded against its tenant with model, units and cost.
- [x] The allowance is checked **before** a billable call; a test proves an exhausted tenant makes no model call at all.
- [x] Exhausted quota returns the typed 402 failure from both run-start and revise.
- [x] The interface shows consumption against allowance, and explains clearly when work is refused for quota. **Engine half only** — see Completion.
- [x] A per-deliverable revision cap and a per-campaign run cap are enforced.
- [x] Cost accounting is distinct from the campaign budget, which is the business's media spend.
- [x] Ledger entries are queryable per tenant and per campaign.
- [x] `uv run pytest`, `uv run ruff check .`, `uv run ruff format`, `uv run mypy src` all pass.
- [x] Verified in the running app.

## Blocked by

- [05 — Postgres: adapter, durable checkpointer, shared run registry](archive/05-postgres-adapter-durable-checkpointer-shared-registry.md)

## Completion

- Completed: 2026-09-03
- Commits: `8d43b48` (implementation)
- Commit: 8d43b48017616ec3292446ba0f9fb895be5135c9

### Evidence per criterion

1. **Recorded with model, units and cost** — `build_entry` in `agent-harness/src/marketing_os/adapters/usage.py` sets all three; `_charge` records after both the specialist and the review call (`graph/nodes.py`). Test: `test_recorded_units_and_cost_name_the_model_that_was_billed`.
2. **Checked before the call** — `ledger.check()` runs before `agent.ainvoke` and before `reviewer.areview`. Test: `test_an_exhausted_tenant_makes_no_model_call_at_all` asserts the scripted model recorded zero calls and that spend did not move.
3. **Typed 402 from run-start and revise** — `QuotaExhaustedError` (402, `quota_exhausted`); `_refuse_when_quota_spent` guards `run`, `revise` and `reopen`. Tests: `test_an_exhausted_tenant_is_refused_a_run_with_the_typed_402`, `..._a_revision_...`, `..._a_reopen`.
4. **Consumption against allowance** — **engine half done**: `GET /usage` returns used/allowance/remaining/exhausted plus a per-campaign breakdown, and the refusal carries a plain-English message; both are in the frozen contract (`UsageReport`, `QuotaExhaustedError`). The **web UI half is deliberately deferred** to slice 12, which rebuilds Home from real data — wiring it here would have been overwritten. Carried forward onto `12-remaining-screens-wired.md`.
5. **Both caps** — the per-deliverable revision cap pre-dates this slice (07); the per-campaign run cap is new (`RunLimitError`, `_refuse_when_runs_spent`). Tests: `test_a_campaign_cannot_be_run_past_its_run_cap`, `test_reopening_a_stage_is_bounded_by_the_run_cap`, `test_the_run_cap_is_per_campaign_not_per_tenant`.
6. **Distinct from campaign budget** — stated in the `/usage` docstring and the contract description; CONTEXT.md's **Campaign Budget** and new **Allowance** entries keep the two apart.
7. **Queryable per tenant and per campaign** — `entries(tenant, slug)` and `consumption(tenant, slug)`, proven against **both** adapters by one conformance suite (`test_usage_ledger.py`).
8. **Gates** — `ruff check`, `ruff format --check`, `mypy src` clean; **499 tests pass** with `MARKETING_OS_TEST_POSTGRES=1` (zero skips). Contract lints clean under Spectral.
9. **Verified in the running app** — driven against real containerised Postgres: 11 checks passed, including a refused request leaving spend unmoved at `2.04000` (no model call), and ledger rows persisted with correct attribution.

### Notes for later

- **Code review** found one real defect, since fixed: the `CampaignUsage` schema this slice added required `campaign_id` while the handler returned `slug`. Now `slug` throughout, matching CONTEXT.md's **Campaign Slug** glossary entry (`_Avoid_: id, name, key`).
- **Pre-existing vocabulary drift, not fixed here:** the rest of the contract says `campaign_id` (`cmp_spring`) while every engine endpoint speaks `slug`. Out of scope for this slice; worth its own issue.
- **Adapter asymmetry:** the Postgres ledger writes a per-tenant allowance onto the existing `tenants` row, so it no-ops for a tenant the directory has not registered, where the in-memory one accepts it. Harmless in production (a tenant exists before it spends) but real.

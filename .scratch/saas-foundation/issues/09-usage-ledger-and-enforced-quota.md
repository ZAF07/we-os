# 09 — Usage ledger and enforced quota

Status: ready-for-agent
Type: task

## Parent

[PRD: we-OS SaaS foundation](../PRD.md) · [ADR-0020](../../../docs/adr/0020-usage-ledger-and-enforced-quota.md)

## What to build

Every billable model call is recorded against its tenant with its cost, and the tenant's allowance is checked **before** the call rather than after.

Today the only cost telemetry is per-run token usage folded into the run result — neither persisted per tenant nor capped — and the QA iteration limit bounds only the *automated* revision loop. Nothing bounds human revision, which slice 07 just introduced. With image generation arriving in a later PRD, one business clicking "try again" repeatedly costs real money with no ceiling and no record.

Exceeding the allowance raises a typed quota failure, surfaced as **402**, so starting a run and revising a stage both carry that outcome in their contract. An endpoint that cannot fail with "quota exceeded" is an endpoint whose contract has to change later — which is why this is built while pre-revenue rather than after.

Hard caps sit alongside the ledger: a maximum number of revisions per deliverable, and runs per campaign.

How the allowance is *presented* — credits, fair use on a flat plan, metered billing — is deliberately out of scope. The mechanism is not.

The ledger doubles as the unit-economics dataset: what a campaign, a revision, and a business actually cost.

End-to-end behaviour: run campaigns until the allowance is exhausted, see work refused with a clear message rather than a generic error, and see consumption reflected in the interface throughout.

## Acceptance criteria

- [ ] Every billable model call is recorded against its tenant with model, units and cost.
- [ ] The allowance is checked **before** a billable call; a test proves an exhausted tenant makes no model call at all.
- [ ] Exhausted quota returns the typed 402 failure from both run-start and revise.
- [ ] The interface shows consumption against allowance, and explains clearly when work is refused for quota.
- [ ] A per-deliverable revision cap and a per-campaign run cap are enforced.
- [ ] Cost accounting is distinct from the campaign budget, which is the business's media spend.
- [ ] Ledger entries are queryable per tenant and per campaign.
- [ ] `uv run pytest`, `uv run ruff check .`, `uv run ruff format`, `uv run mypy src` all pass.
- [ ] Verified in the running app.

## Blocked by

- [05 — Postgres: adapter, durable checkpointer, shared run registry](archive/05-postgres-adapter-durable-checkpointer-shared-registry.md)

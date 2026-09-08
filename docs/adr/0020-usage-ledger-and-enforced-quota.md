# Usage ledger and enforced per-tenant quota, from day one

Every billable call — model tokens and image generations — is recorded in a Postgres usage ledger against its tenant, with its cost. The engine checks the tenant's remaining allowance **before** each billable call and records after; exceeding it raises a typed quota error, surfaced as HTTP 402, so `run`, `revise`, and `regenerate` carry that failure mode in their contract from the start. Hard caps sit alongside it: a maximum number of revisions per creative unit, and runs per campaign.

Today the only cost telemetry is per-run token `Usage` folded into `CampaignResult`, neither persisted per tenant nor capped, and `MARKETING_OS_MAX_QA` bounds only the *automated* revision loop. Nothing bounds human reiteration. With image generation landing, one business clicking "try again" forty times on a creative unit costs real money with no ceiling and no record.

Enforcement is built while pre-revenue, before there is pressure to ship without it, because retrofitting cost checks into an agentic loop is genuinely painful and an endpoint that cannot fail with "quota exceeded" is an endpoint whose contract has to change later. How the allowance is *presented* — credits, fair use on a flat plan, metered billing — stays a later decision; the mechanism does not.

## Consequences

- The ledger doubles as the unit-economics dataset: what a campaign, a revision, and a tenant actually cost.
- Distinct from campaign budget, which is the business's media/ad spend ([ADR-0016](0016-channel-planning-precedes-creative.md)).

## Amendment (2026-09-08)

The presentation is decided: the allowance is shown to a business as **credits**, granted per tier each month. The engine still meters real cost; the cost-to-credit rate is set in one place and is not yet fixed. See **Credits** and **Tier** in `CONTEXT.md`.

## Amendment (2026-09-08, second)

The `allowance` identifier is renamed to `credits` throughout — the `tenants` column, the platform default (now `MARKETING_OS_CREDITS`), the usage report field, the 402 detail key, the ledger port, the adapters, the OpenAPI contract, and the web client. A guarded `RENAME COLUMN` carries a database provisioned under the old name across and is a no-op otherwise. Behaviour is unchanged by the rename.

The cost-to-credit rate is now real: `MARKETING_OS_CREDIT_RATE` says how many credits one unit of recorded cost burns, defaulting to 1 so nothing moves until it is set. The ledger still records real cost — it remains the unit-economics dataset — and credits are derived from it in one place, shared by both ledger adapters. The usage report shows whole credits (round half up); the quota check compares the unrounded value, so display rounding never decides a refusal.

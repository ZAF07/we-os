# Usage ledger and enforced per-tenant quota, from day one

Every billable call — model tokens and image generations — is recorded in a Postgres usage ledger against its tenant, with its cost. The engine checks the tenant's remaining allowance **before** each billable call and records after; exceeding it raises a typed quota error, surfaced as HTTP 402, so `run`, `revise`, and `regenerate` carry that failure mode in their contract from the start. Hard caps sit alongside it: a maximum number of revisions per creative unit, and runs per campaign.

Today the only cost telemetry is per-run token `Usage` folded into `CampaignResult`, neither persisted per tenant nor capped, and `MARKETING_OS_MAX_QA` bounds only the *automated* revision loop. Nothing bounds human reiteration. With image generation landing, one business clicking "try again" forty times on a creative unit costs real money with no ceiling and no record.

Enforcement is built while pre-revenue, before there is pressure to ship without it, because retrofitting cost checks into an agentic loop is genuinely painful and an endpoint that cannot fail with "quota exceeded" is an endpoint whose contract has to change later. How the allowance is *presented* — credits, fair use on a flat plan, metered billing — stays a later decision; the mechanism does not.

## Consequences

- The ledger doubles as the unit-economics dataset: what a campaign, a revision, and a tenant actually cost.
- Distinct from campaign budget, which is the business's media/ad spend ([ADR-0016](0016-channel-planning-precedes-creative.md)).

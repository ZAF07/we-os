# Organic publishing before paid ads

Platform integration ships in two milestones behind a `PublishTarget` port, organic first: an approved creative unit is scheduled and posted to the business's connected Instagram/Facebook Page and TikTok, with reach and engagement read back to feed the Measure lifecycle. Paid ads — the campaign → adset → ad hierarchy, targeting derived from the Performance Plan, spend guardrails and policy pre-checks — follow as a second milestone.

Organic goes first because the blast radius is smaller. A weak post costs nothing; a bad ad spends a stranger's money and can get their business ad account restricted. Running ads on behalf of a business is a genuine liability surface — their account, their payment method, their spend — and an autonomous system that generates creative which might trip platform ad policy needs approval gates and policy pre-checks that do not exist yet. Organic also proves the whole publish loop end to end (OAuth per tenant, encrypted token storage, refresh and revocation, scheduling, the calendar screen, results read-back) against a much smaller data model.

## Consequences

- **App review is calendar time, not engineering time, and it is the long pole.** Meta requires Business Verification plus Advanced Access for publishing and ads scopes; TikTok restricts unaudited apps to self-only posting until audited, and link posting needs domain verification. These take weeks, and need a working demo, a privacy policy, and terms. **Both applications start at the beginning of the project, in parallel with the foundation work — not when the integration code is ready.** Verify current requirements against the platforms' live documentation; they change often.
- Per-tenant platform access tokens are secrets at rest and need encryption and a rotation story — the system has no secret store today.
- The Performance Plan stage must eventually emit platform-shaped targeting specifications, which it does not currently produce.

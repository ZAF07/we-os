# One business per tenant, with dual-verified JWT identity

we-OS is a SaaS agentic platform sold to **a business**, as a cheaper alternative to hiring a marketing team or retaining an agency. It is **not** an agency platform: a tenant is one business, marketing itself. A tenant does not manage other businesses on the platform, so the model is one tenant → one Brand DNA → many campaigns. The people a business sells to are **audience segments** described *inside* its Brand DNA, not entities the tenant administers.

Identity comes from a managed IdP issuing JWTs. The Next.js BFF verifies the token for page rendering **and** forwards it to the FastAPI engine, which verifies it independently and derives `tenant_id` from the verified claim. No endpoint accepts a business identity as a caller-supplied parameter.

## Considered options

- **Dual verification (chosen)** — costs one extra verification hop; buys an engine that stays tenant-safe even when reached directly by a misconfigured ingress, a future background worker, or a bug.
- **BFF holds the session; FastAPI trusts a service token and a tenant header** — rejected: the engine would have no independent notion of who it works for, so any path reaching it directly bypasses tenancy entirely. With platform access tokens and ad spend in the database, that failure is unrecoverable.
- **Roll our own auth in FastAPI** — rejected: weeks of undifferentiated work (password reset, email verification, OAuth login, session management) before a single campaign runs.

## Consequences

- The current API takes `customer` as a request field and `slug` as a path param, neither checked against the caller — safe only while single-user and unexposed. Under one-business-per-tenant the `customer` parameter is **fully redundant** with the verified claim and is removed rather than validated.
- The `customers/<name>/` collection is agency-shaped and collapses to a Brand DNA singleton owned by the tenant (see [ADR-0022](0022-brand-dna-and-the-overloaded-customer.md)).
- Tenant scoping is enforced in the repository/DocumentStore layer — and backstopped by Postgres row-level security — never at individual call sites, so a forgotten `WHERE` clause cannot leak across tenants. Implementing this found three places where the pre-tenancy code did not honour it; see [ADR-0023](0023-tenant-partitioned-storage-and-a-sandbox-that-serves-no-tenant-data.md) for what leaked and how partitioning closed it.
- Every existing endpoint changes shape, which is why FE↔BE wiring cannot precede this work.

## Amendment (2026-09-09)

Dual verification carries an inter-service contract that was implicit until it
broke: **the engine's clock-skew tolerance must be at least the BFF's, plus the
hop between them.** The BFF forwards the session token it accepted, and it
accepts one up to 5 seconds past `exp` (Clerk's default `clockSkewInMs`), so an
engine that verified with zero leeway refused every token in the 5 seconds
after its expiry — a burst of 401s, once per token lifetime, that surfaced as a
shifting handful of e2e failures (`.scratch/e2e-suite-flake`, issue 01).

The engine now verifies `exp`, `nbf` and `iat` with a 10-second leeway, the
tolerance Clerk itself encodes by dating `nbf` 10 seconds before `iat`. Anyone
raising the BFF's `clockSkewInMs` above that must raise the engine's leeway
with it; a token the BFF trusts and the engine refuses is the failure mode this
amendment exists to name.

## Amendment — a refusal is opaque to the caller, not to the operator (2026-09-09)

The uniform 401 above is a decision about **the caller**, and it stands: every
way a token can fail — absent, malformed, expired, not yet valid, wrongly
signed, wrong issuer or audience, carrying no organization — answers the same
status and the same "Sign in to continue.", so a probe learns nothing from a
refusal.

That opacity was never meant for the operator, and treating it as though it
were is what made the amendment above expensive to reach: the engine wrote
nothing when it said no, so diagnosing issue 01 took twelve suite runs and a
hand-patched container to establish a fact the engine already knew.

The two audiences are now separated. The response is unchanged, and each
refusal writes one INFO line under `marketing_os.auth` naming its failure class
and the request path; for a decodable token the line also carries `exp` and
`iat` as offsets from the engine clock, which is what makes a skew or expiry
window visible at a glance rather than inferable over a dozen runs. The failure
classes are a closed set (`RefusalClass`), so a refusal cannot be logged under a
name nothing else uses.

What the log must never carry is the other half of the contract: **not the token,
and no claim beyond those two timestamps.** A refusal log that echoed the
credential would hand an attacker with log access what the 401 was written to
withhold, and it is asserted by test rather than left to care.

Anyone adding a refusal path adds its class here too. A path that refuses
silently is the condition this amendment exists to prevent — the caller-facing
answer is the same either way, so silence is invisible until someone is
debugging it under time pressure.

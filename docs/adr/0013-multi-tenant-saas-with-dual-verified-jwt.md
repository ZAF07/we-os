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
- Tenant scoping is enforced in the repository/DocumentStore layer — and backstopped by Postgres row-level security — never at individual call sites, so a forgotten `WHERE` clause cannot leak across tenants.
- Every existing endpoint changes shape, which is why FE↔BE wiring cannot precede this work.

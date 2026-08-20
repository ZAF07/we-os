# 04 — Tracer bullet: one authenticated tenant, end to end

Status: ready-for-agent
Type: task

## Parent

[PRD: we-OS SaaS foundation](../PRD.md) · [ADR-0013](../../../docs/adr/0013-multi-tenant-saas-with-dual-verified-jwt.md) · [ADR-0022](../../../docs/adr/0022-brand-dna-and-the-overloaded-customer.md)

## What to build

The thinnest complete path through every layer, proving the architecture before the expensive slices commit to it. A real person logs in and drives a real campaign end to end.

The path: sign in against the managed IdP → the frontend verifies the token and forwards it → the engine verifies it **independently** and derives the tenant from the verified claim → the tenant's Brand DNA is read through the `DocumentStore` → the DNA Gate reports completeness → a run starts → a deliverable is read back and rendered in the browser.

Two structural changes land with it:

- **The `customer` parameter is removed**, not validated. A tenant is one business ([ADR-0022](../../../docs/adr/0022-brand-dna-and-the-overloaded-customer.md)), so a caller-supplied business identity is fully redundant with the verified claim — and accepting one is exactly what ADR-0013 forbids. This covers the operation bodies, the query parameters, the CLI argument, and the graph state key.
- **Tenant scoping is enforced inside the `DocumentStore`**, not at call sites, so new code cannot forget it.

Storage stays on the filesystem adapter — Postgres is slice 05. The point of this slice is to prove identity, tenancy and the full round trip, not persistence.

The frontend contribution is deliberately thin: a real sign-in, and one screen showing the tenant's DNA completeness and a deliverable. The designed screens are wired in slices 10–12.

## Acceptance criteria

- [ ] A user signs in through the IdP and reaches an authenticated screen.
- [ ] The engine verifies the token itself and rejects a request with no token, an expired token, and a token with an invalid signature.
- [ ] A request carrying a valid identity for a different tenant is refused for every resource type — Brand DNA, campaign, run, deliverable.
- [ ] No operation, CLI argument, or graph state key accepts a business identity from the caller.
- [ ] Tenant scoping is enforced in the storage layer; a test proves a repository call without an explicit scope cannot return another tenant's document.
- [ ] The DNA Gate refuses a run when Required fields are missing and names every missing field.
- [ ] A run started from the browser completes, and its deliverable is fetched and rendered.
- [ ] The auth dependency is overridable in tests to inject a verified claim; no test contacts a live IdP.
- [ ] `uv run pytest`, `uv run ruff check .`, `uv run ruff format`, `uv run mypy src` all pass.
- [ ] Verified in the running app, not only in tests.

## Blocked by

- [02 — Introduce the DocumentStore port](02-introduce-documentstore-port.md)
- [03 — Freeze the API contract and stand up a mock server](03-freeze-api-contract-and-mock-server.md)

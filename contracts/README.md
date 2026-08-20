# we-OS API contract

`openapi.yaml` is the **frozen contract** between the frontend and the engine
(ADR-0017, `.scratch/saas-foundation/PRD.md`). The frontend codes against the
mock server serving this document; the engine is built behind it. The contract
is a design deliverable and will change — deliberately, visibly to both sides,
in review.

Two invariants the linter enforces (`.spectral.yaml`):

- **No operation accepts a tenant, business, or customer identity as a
  parameter** — identity comes only from the verified bearer token, and
  cross-tenant access resolves to an indistinguishable `404 not_found`.
- Every operation is tagged and named.

## Commands

```bash
npm install        # once
npm run lint       # Spectral — must stay error-free (CI-gated)
npm run mock       # Prism mock server on http://localhost:4010
npm test           # spins up Prism and drives the operator happy path
```

The mock serves the spec's examples. Named variants are selected per request
with `Prefer: example=<name>` (e.g. `example=awaiting-approval` on
`GET /runs/{runId}`), and error shapes with `Prefer: code=<status>`.

`happy-path.mjs` is the executable proof the frontend can complete the core
journey with no engine present: sign in → DNA completeness → create campaign →
start run → hit the brand-strategy approval gate → approve → read the
deliverable — plus the frozen error shapes (401 unauthenticated, 404
cross-tenant, 409 gate failure with named missing fields, 409 run conflict,
402 quota exhaustion).

CI runs the lint and the happy path on any change under `contracts/`
(`.github/workflows/contract.yml`).

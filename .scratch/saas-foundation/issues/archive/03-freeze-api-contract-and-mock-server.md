# 03 — Freeze the API contract and stand up a mock server

Status: completed
Type: task

## Parent

[PRD: we-OS SaaS foundation](../PRD.md) · [ADR-0017](../../../docs/adr/0017-stages-and-lifecycle-are-separate-axes.md)

## What to build

The OpenAPI specification for the **whole target API**, not just what exists today, plus a mock server serving it. This is the artifact the frontend codes against, so FE and engine work proceed in parallel from here instead of the FE idling through slices 04–09.

The contract must settle, at minimum:

- Authentication: how identity is carried, and the shape of an unauthenticated and a cross-tenant refusal. **No operation takes a business identity as a parameter.**
- Brand DNA: read, the completeness report, and answering questionnaire questions.
- Questionnaire: fetching the current published question set, including each question's text, why it is asked, help text, input type, and whether it is Required.
- Campaigns: create with goal fields and all three KPI tiers, list, read, archive.
- Stages: each reporting its key, its operator **Phase**, its state, and its approval policy — the API speaks engine stages, and the Phase grouping lets the frontend render its designed stepper without the engine adopting UI vocabulary.
- Campaign lifecycle status as a **separate field** from stage progress: `draft`, `running`, `awaiting_approval`, `approved`, `published`, `measuring`, `archived`.
- Runs: start, status, cancel, live progress stream, **approve**, **revise with feedback**.
- Deliverables: read content, list versions, read a specific version with the feedback that produced it, and a stale indicator.
- Errors: the existing pattern of a typed error carrying its own status and structured detail, extended with quota exhaustion as 402 and gate failure listing every missing Required field.

End-to-end behaviour: the frontend runs against the mock server and can drive a complete happy path — sign in, see the DNA completeness report, create a campaign, start a run, hit an approval gate, approve, read a deliverable — with no engine present.

The contract is a design deliverable and is expected to change; the point is that changes are then deliberate and visible to both sides.

## Acceptance criteria

- [x] An OpenAPI document covers every operation listed above and is committed to the repo.
- [x] No operation accepts a tenant, business, or customer identity as a caller-supplied parameter.
- [x] Stage responses carry both the engine stage key and its operator Phase; lifecycle status is a distinct field.
- [x] Deliverable responses expose content, version, supersession and staleness.
- [x] The error schema covers gate failure with named missing fields, quota exhaustion, run conflict, and cross-tenant refusal.
- [x] A mock server serves the spec and the frontend can complete the happy path against it.
- [x] The spec validates against an OpenAPI linter in CI.

## Blocked by

None - can start immediately.
## Comments

- Contract at `contracts/openapi.yaml` (OpenAPI 3.0.3). Mock is Prism serving the
  spec's examples; named variants select via `Prefer: example=<name>` and error shapes
  via `Prefer: code=<n>`. `contracts/happy-path.mjs` is the executable proof of the
  no-engine happy path (21 checks, all passing locally).
- `.spectral.yaml` extends `spectral:oas` with two custom rules: no operation parameter
  and no schema property may carry a tenant/business/customer identity, so the
  no-tenant-parameter invariant is machine-enforced, not just reviewed.
- CI: `.github/workflows/contract.yml` runs the lint and the happy path on any change
  under `contracts/` — first workflow in the repo; it runs once this lands on GitHub.
- Cross-tenant refusal is frozen as an indistinguishable 404 `not_found` (documented in
  the spec's Tenancy section) rather than a 403, so existence never leaks.

## Completion

- Completed: 2026-08-20
- Commit: <to be filled in manually>

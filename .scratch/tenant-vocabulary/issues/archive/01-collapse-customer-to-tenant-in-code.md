# Collapse `customer` to the tenant in the harness code

Status: completed

Blocked by: the Postgres migration ([ADR-0014](../../../docs/adr/0014-postgres-system-of-record-and-split-governance.md)) — see Sequencing.

The vocabulary pass renaming Customer DNA → Brand DNA landed across the glossary, ADRs, governance markdown, templates, guardrails and operator docs ([ADR-0022](../../../docs/adr/0022-brand-dna-and-the-overloaded-customer.md)). The code was deliberately left for a second pass, because what remains is a **behavioural change, not a rename**.

## What's needed

- **Remove the `customer` parameter.** `CreateCampaign.customer`, `RunCampaign.customer`, `GET /campaigns/{slug}/gate?customer=`, the CLI's customer argument, and `CampaignState["customer"]` all pass a business identity as a caller-supplied value. Under one business per tenant it is fully redundant with the verified tenant claim, and [ADR-0013](../../../docs/adr/0013-multi-tenant-saas-with-dual-verified-jwt.md) forbids accepting it from the caller.
- **Collapse `customers/<name>/dna.md` to a tenant-owned Brand DNA singleton.** Touches `Settings.customers_dir`, `check_gate`, and the gate node in `graph/nodes.py`.
- **Rename the remaining ~210 identifiers and docstrings** across `agent-harness/src` and `agent-harness/tests` so "customer" means only "a person the business sells to".

## Sequencing

Do this **with or after** the Postgres migration, not before. The migration removes the `customers/<name>/` layout entirely, so renaming the filesystem plumbing first is churn the migration redoes.

## Acceptance criteria

- [x] No endpoint, CLI argument, or graph-state key accepts a business identity from the caller.
- [x] `grep -ri customer agent-harness/src` returns only references to the people a business sells to (audience segments).
- [x] `uv run pytest`, `uv run ruff check .`, `uv run ruff format`, `uv run mypy src` all pass.
- [x] The Stage 0 gate still blocks on an incomplete Brand DNA, with a test proving it.

## Evidence

- Vocabulary pass verified green at the time of writing: 189 passed, 1 skipped; ruff and mypy clean.
- `.claude/rules/brand-dna.md` now carries the binding vocabulary rule agents load every session.

## Completion

- Completed: 2026-09-02
- Commit: `1254212` — "implemented .scratch/saas-foundation/issues/04-tracer-authenticated-tenant-end-to-end.md" (2026-08-30)

The work landed as a side effect of the SaaS foundation tracer, not as a separate
pass. Commit `1254212` introduced the verified-identity dependency and the
tenant-scoped `DocumentStore`, which removed the caller-supplied `customer`
parameter from the API, CLI and graph state, replaced `Settings.customers_dir`
with `tenants_dir`, and collapsed `customers/<name>/dna.md` to the tenant-owned
`dna.md` singleton — all in one commit. `git log -S` confirms it is the sole
commit touching `customers_dir`, `tenants_dir`, and the `customer` key in
`graph/state.py`.

### Verification (2026-09-02)

- **No caller-supplied business identity.** Every endpoint in
  `entrypoints/api/app.py` takes the tenant from the verified `Identity`
  dependency — `create_campaign` (L414), `gate` (L449, no `?customer=`),
  `run` (L521). `entrypoints/cli.py:34-52` resolves the tenant from
  `MARKETING_OS_TENANT_ID` and documents why a caller-typed identity is refused.
  `CampaignState` carries `tenant` (`graph/state.py:56`), not `customer`.
- **Brand DNA singleton.** `check_gate` reads the logical document `dna.md`
  (`governance/gate.py:141`); `graph/nodes.py:201-215` documents that the tenant
  never appears in a model-visible path. `Settings.customers_dir` is gone,
  replaced by `tenants_dir` (`config.py:278`).
- **Rename.** `grep -ri customer agent-harness/src` returns one hit —
  `governance/pipeline.py:52` ("Produce customer, competitor, market...") — which
  is the correct sense: people the business sells to. `tests/test_tenancy.py:369`
  is a standing guard asserting `Settings` exposes no customer vocabulary.
- **Gate still blocks.** `tests/test_gate.py:44` (placeholder) and `:52`
  (missing files) prove it.
- **Quality gates.** 278 passed, 23 skipped; `ruff check` clean; 77 files already
  formatted; `mypy src` clean across 51 source files.

### Follow-up filed separately

`agent-harness/README.md` (L71-89) and `agent-harness/USAGE.md` (L51-100) still
document the removed interface: `POST /campaigns {customer, slug?}`,
`GET /campaigns/{slug}/gate?customer=`, `marketing-os check <customer>`, and an
SSE endpoint at `/campaigns/{slug}/stream` that is now `/runs/{run_id}/stream`.
Documentation drift, not a behavioural gap — out of scope for this issue.

# Collapse `customer` to the tenant in the harness code

Status: ready-for-agent

Blocked by: the Postgres migration ([ADR-0014](../../../docs/adr/0014-postgres-system-of-record-and-split-governance.md)) — see Sequencing.

The vocabulary pass renaming Customer DNA → Brand DNA landed across the glossary, ADRs, governance markdown, templates, guardrails and operator docs ([ADR-0022](../../../docs/adr/0022-brand-dna-and-the-overloaded-customer.md)). The code was deliberately left for a second pass, because what remains is a **behavioural change, not a rename**.

## What's needed

- **Remove the `customer` parameter.** `CreateCampaign.customer`, `RunCampaign.customer`, `GET /campaigns/{slug}/gate?customer=`, the CLI's customer argument, and `CampaignState["customer"]` all pass a business identity as a caller-supplied value. Under one business per tenant it is fully redundant with the verified tenant claim, and [ADR-0013](../../../docs/adr/0013-multi-tenant-saas-with-dual-verified-jwt.md) forbids accepting it from the caller.
- **Collapse `customers/<name>/dna.md` to a tenant-owned Brand DNA singleton.** Touches `Settings.customers_dir`, `check_gate`, and the gate node in `graph/nodes.py`.
- **Rename the remaining ~210 identifiers and docstrings** across `agent-harness/src` and `agent-harness/tests` so "customer" means only "a person the business sells to".

## Sequencing

Do this **with or after** the Postgres migration, not before. The migration removes the `customers/<name>/` layout entirely, so renaming the filesystem plumbing first is churn the migration redoes.

## Acceptance criteria

- [ ] No endpoint, CLI argument, or graph-state key accepts a business identity from the caller.
- [ ] `grep -ri customer agent-harness/src` returns only references to the people a business sells to (audience segments).
- [ ] `uv run pytest`, `uv run ruff check .`, `uv run ruff format`, `uv run mypy src` all pass.
- [ ] The Stage 0 gate still blocks on an incomplete Brand DNA, with a test proving it.

## Evidence

- Vocabulary pass verified green at the time of writing: 189 passed, 1 skipped; ruff and mypy clean.
- `.claude/rules/brand-dna.md` now carries the binding vocabulary rule agents load every session.

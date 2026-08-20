# Populate the Knowledge Library with expert frameworks

Status: ready-for-human

All five discipline folders under `knowledge/` ship as stubs with `TODO` markers. Agents currently cite standard, well-known frameworks inline (e.g. JTBD, competitor positioning matrix, April Dunford positioning) rather than project-specific ones, because the library is empty.

## What's needed

Fill each discipline with the reusable, citable frameworks its agent reads:

- `knowledge/research/` — research methods, source-quality bar, segmentation model.
- `knowledge/brand/` — positioning model, messaging hierarchy, voice guidelines.
- `knowledge/creative/` — brief template, concept criteria, prompt templates, format/channel specs.
- `knowledge/performance/` — channel benchmarks, KPI targets, budget model, optimization rules.
- `knowledge/frameworks/` — cross-cutting marketing & advertising frameworks.

This is domain-expert content, not code. The library is read-only to agents in this version.

## Evidence

- `knowledge/{research,brand,creative,frameworks,performance}/README.md` (each carries a `<!-- TODO: add ... -->` marker).
- `knowledge/README.md` (structure + read-only note).

## Comments

**2026-08-20.** The knowledge library is now classed as admin-tunable content and moves into Postgres ([ADR-0014](../../../docs/adr/0014-postgres-system-of-record-and-split-governance.md)). The work is unchanged — domain-expert content, not code — but if the migration has landed, author it in the admin surface rather than in `knowledge/<discipline>/`.

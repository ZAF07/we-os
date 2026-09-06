# 05 — One markdown field format, one module

Status: ready-for-agent
Type: task

## Parent

[ADR-0003](../../../docs/adr/0003-governance-as-markdown.md) · [ADR-0018](../../../docs/adr/0018-human-authored-dna-from-a-curated-questionnaire.md)

## Why

`- **Label:** value` is the contract between what the Questionnaire renders and
what the DNA Gate reads. It is agreed in three docstrings and enforced by nothing.

`_FIELD_RE` is defined identically in two modules —
`governance/gate.py:37` and `campaign/goal.py:40` — and the same three-branch
section walk is written twice (`gate.py:55,78`; `goal.py:227,329`).
`questionnaire/render.py:31,68` writes the format a third module has to parse.

ADR-0018 makes the Brand DNA human-authored and machine-read. This format is the
seam between the business's answers and the gate that admits them, and a
render → parse round trip is currently guaranteed by nothing.

## Scope

A top-level `markdown.py` owning `parse`, `render`, and required-label
extraction, including the placeholder (`<...>`) and multi-line value rules.
`gate.py`, `goal.py` and `questionnaire/render.py` call it.

**Placement.** Top level, beside `schemas.py` / `ports.py` / `errors.py` — not
under `governance/`. The three consumers are sibling packages that do not import
each other today (the one cross-package edge is `governance → questionnaire`).
Putting the format under `governance/` would add two upward edges and place the
module that *writes* the format below the package that *reads* it. Shared
vocabulary lives at the root; packages sit above it.

## Acceptance criteria

- [ ] `_FIELD_RE` is defined once; `gate.py` and `goal.py` no longer carry their own.
- [ ] The section walk exists in one place.
- [ ] A property test asserts render → parse round-trips, including multi-line values and placeholders.
- [ ] Placeholder and multi-line rules are stated once, in the module, not in three docstrings.
- [ ] No new package coupling: `campaign/` and `questionnaire/` do not import `governance/`.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` all pass.

## Comments

**2026-09-06.** Review candidate **10**. Placement was decided against the
review's implied `governance/markdown.py` after checking the existing import
directions — see Scope.

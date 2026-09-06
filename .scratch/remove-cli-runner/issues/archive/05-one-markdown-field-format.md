# 05 — One markdown field format, one module

Status: completed
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

- [x] `_FIELD_RE` is defined once; `gate.py` and `goal.py` no longer carry their own.
- [x] The section walk exists in one place.
- [x] A property test asserts render → parse round-trips, including multi-line values and placeholders.
- [x] Placeholder and multi-line rules are stated once, in the module, not in three docstrings.
- [x] No new package coupling: `campaign/` and `questionnaire/` do not import `governance/`.
- [x] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` all pass.

## Comments

**2026-09-06.** Review candidate **10**. Placement was decided against the
review's implied `governance/markdown.py` after checking the existing import
directions — see Scope.

## Completion

- Completed: 2026-09-07
- Commit: `7da05ad` — Campaign progress and the markdown field format become core modules

Top-level `markdown.py` owns the format: `render_field`, `parse_fields`,
`walk_fields`, `is_placeholder` and `labels_under_heading`. `_FIELD_RE` is
defined once, the section walk exists once, and the multi-line and placeholder
rules are stated in the module rather than re-explained in three docstrings.
`gate.py`, `goal.py` and `questionnaire/render.py` all call in, and no new
package edge appeared — the module is at the root, so `campaign/` and
`questionnaire/` import it rather than `governance/`.

**The round trip did not hold, and now does.** Writing the property test found
it: `render_field` wrote `  - Commuters` and the parser returned `- Commuters`,
indentation and bullet included, so an answer did not survive being written and
read back. Pre-existing — verified against the previous commit, where
`field_map` returned the same — and precisely the guarantee this issue says was
guaranteed by nothing. `walk_fields` now strips the markup a continuation line
is carried by, and `audience_segments` dropped the `.lstrip("-*")` it had been
compensating with.

Hypothesis was added as a dev dependency so the criterion's *property* test is a
real one rather than a table standing in for it. Both are kept: the generated
property says the round trip holds for arbitrary labels and answers, and a table
beside it pins the cases the format deliberately normalises — an already-bulleted
answer, a blank line inside a value, a line that is only markup.

Code review (`/code-review`, both axes) found three things worth fixing:

1. **An empty bullet counted as a filled Required field.** `_continuation` fell
   back to returning the line's own markup when stripping left nothing, so a
   bare `-` parsed to `"-"`, which `is_placeholder` reads as filled — the gate
   would admit a Required question the business never answered. Such lines now
   come back empty. Covered by `test_an_empty_bullet_is_not_a_filled_field`.

2. **The round-trip test agreed with the parser instead of checking it.** Its
   oracle re-implemented `_continuation`'s own stripping rule, so a wrong parser
   would have passed. The property now asserts plain equality over values the
   format does not normalise, and the normalised cases are asserted as their
   stated results.

3. **`render_campaign_goal` was a fourth writer of the format**, hand-writing
   `f"- **{label}:** {value}"` in eight places, so the round trip did not hold
   for `goal.md`: a multi-line objective was truncated, and a value containing
   `## text` silently lost everything after it. It renders through
   `render_field` now, and both cases round-trip.

Also: `FIELD_RE` made private to match its sibling `_PLACEHOLDER_RE`, the
one-caller `_render_field` wrapper in `questionnaire/render.py` inlined, and
`parse_campaign_goal`'s `markdown` parameter renamed to `document` — it shadowed
the module the same file imports from.

Verified against a running stack: `make test-e2e` passes 42–43/43. The one
intermittent failure is `onboarding.spec.ts` "completing the questionnaire lands
on the Brand screen with the answers", and it is **not** a regression: three
clean full runs of this branch and three of the parent commit both failed twice
out of three, at the same assertion, with the same cause. The spec fills only
four of the wizard's five steps and so depends on an earlier spec having saved
step 1; when that ordering does not hold, `q_business_name` keeps the earlier
spec's "Acme Coffee". Confirmed in the database, and the spec passes on a clean
tenant. It is the flake first seen in [01](01-remove-the-campaign-driving-cli.md)
and is worth filing on its own.

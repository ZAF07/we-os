# 16 — The Performance screen shows a plan's sections but cannot tell you which is the channel mix

Status: ready-for-agent
Type: task

## Parent

[PRD: we-OS SaaS foundation](../PRD.md) · follows [12 — remaining screens wired](archive/12-remaining-screens-wired.md)

## Symptom

[12](archive/12-remaining-screens-wired.md) asked for:

> **Performance** — whatever the Performance Plan deliverable actually contains:
> channel mix, per-channel spend allocation, Placements, and the three KPI tiers.

What shipped renders the plan **by whatever headings the specialist happened to
write**. `web/src/lib/deliverable.ts` splits markdown on `#` lines and the screen
lays each section out identically. That is a real improvement on the first
attempt — which dumped raw markdown with `##` and `**` still visible — but it
does not do what the criterion says.

Concretely, the screen cannot:

- say which section is the channel mix and which is the KPI targets;
- show per-channel spend as an allocation (a share of a budget) rather than as
  prose that happens to mention percentages;
- render Placements as the format specs they are — aspect ratio, dimensions,
  copy limits — which is what makes them actionable for whoever builds the
  creative;
- notice when a plan is **missing** one of the four. A plan with no KPI tiers
  renders as a perfectly tidy screen with one fewer section.

That last one is the part that matters. The three KPI tiers are a hard
constraint — `.claude/rules/operating-principles.md` says every campaign defines
all three — and a screen that reports the plan silently tolerates a plan that
does not.

## Repro

Not a crash; a gap you see by reading.

```bash
make e2e-up
# open http://localhost:3100/performance for a campaign past the Plan stage
```

Every section renders with the same weight. Nothing distinguishes "Channel mix"
from "Notes", and nothing appears if a required part is absent.

## What's needed

The decision is made — see [Decision](#decision). What is left is the work it
scoped:

- Identify each of the four parts from its heading in `web/src/app/performance/page.tsx`
  (or a small helper beside `toSections`), and render each with a treatment that
  suits it.
- Leave unrecognised sections rendering exactly as they do today.
- Replace the docstring in `web/src/lib/deliverable.ts` that argues for
  heading-agnosticism, since the screen above it no longer is.

The three options the issue originally posed are resolved: **structured output
from the engine** is deferred (decision 2), **`wontfix`** was rejected because
identification is cheap and the screen genuinely fails to say what it is showing
(decision 3), and **heading matching** is what ships.

## Acceptance criteria

Revised by the Decision section below — the originals assumed the screen was a
second enforcement point, which it is not.

- [ ] The screen identifies the channel mix, the spend allocation, the Placements and the three KPI tiers as those things, not as anonymous sections.
- [ ] Each identified part carries a visual treatment that suits it — KPI tiers grouped by tier, Placements laid out as specs, spend emphasised — while an unrecognised section still renders as it does today.
- [ ] A section whose heading matches nothing renders plainly rather than breaking or disappearing.
- [ ] `web/src/lib/deliverable.ts` no longer documents heading-agnosticism as the design; its docstring carries the reasoning in the Decision section.
- [ ] A spec asserts on a seeded plan with all four parts, and on one whose headings match nothing.
- [ ] Web gates pass — `pnpm typecheck`, `pnpm lint`, `pnpm format:check`, `pnpm test:unit`.
- [ ] `make test-e2e` still passes.

**Withdrawn** (see Decision):

- ~~A plan missing one of them is visibly incomplete rather than silently shorter.~~ — the guardrail owns this, not the screen.
- ~~Per-channel spend reads as an allocation of the campaign budget.~~ — needs numbers parsed out of prose; deferred with structured output.

## Decision

**2026-09-06**, from a `/grill-with-docs` session. Recorded here rather than as an
ADR: the choice is cheap to reverse (one file, one consumer, no contract change),
so it fails the "hard to reverse" bar — but it is surprising without context, and
that is what this section is for.

### 1. The screen is a **reader**, not a second check

The Performance screen reports a plan that has already been certified complete.
`guardrails/performance-plan.md` already requires all four parts — channel
selection with rationale, placements per channel with format specs, a KPI plan
across all three tiers with concrete targets, and a budget allocation that sums
to the campaign budget — and `LLMReviewer` scores every plan against it before
the stage can reach its Approval Gate.

So the missing-KPI-tier case the symptom section calls "the part that matters"
is **already owned upstream**. A plan reaching the screen without its KPI tiers
is a defect in the rubric or the reviewer, and the honest fix is there — see
[backfill/06](../../backfill/issues/06-sharpen-guardrail-rubrics.md).

Rejected: making the screen a **second check** (a deterministic backstop for a
probabilistic judge). Two reasons. A frontend check can only ask "is there a
heading with this word in it", never "are the targets concrete", so it is the
weaker of the two enforcement points and will drift from the rubric it
duplicates. And a warning banner on the screen makes a reviewer that passed a bad
plan *less* visible, not more.

**Consequence:** acceptance criterion 2 ("a plan missing one of them is visibly
incomplete") is withdrawn. It assumed the second-check framing.

### 2. Heading matching on the frontend, not structured output from the engine

The issue's first option — have the `performance-plan` stage emit the four parts
as structured fields alongside the markdown — was justified almost entirely by
the missing-part detection that decision 1 discards. Without it, the option has
to stand on legibility alone, and it does not: a contract change to
`Deliverable`, an ADR, a schema in `schemas.py`, a specialist-prompt change, and
a fallback path for every plan already in the store — to improve the typography
of one screen.

The brittleness that made heading matching unacceptable in the original framing
changes weight under decision 1. A specialist rewording a heading now means a
section renders **plainly instead of specially** — a cosmetic degradation, not a
missed governance failure.

Two facts made this cheaper than it looks: `toSections` has exactly one consumer
(this screen), and there is no markdown renderer in `web/` — `toSections` +
`plainText` *is* the renderer.

### 3. Scope: identification only, no parsing of prose into numbers

The Performance stage is **not a v1 priority**. It gets more thought once users
have proven the product is worth building on. That sets the investment level
here.

**In scope** — identify the four parts by heading and give each a distinct
visual treatment: the KPI section grouped by tier, placements laid out as specs,
the spend section emphasised, everything else rendered as it is today.

**Out of scope** — extracting numbers from prose. The screen will not compute a
share of budget or parse an aspect ratio out of a bullet. If the specialist
writes `- Meta: 40% (£2,000)`, the screen renders that bullet clearly inside a
section labelled "Spend allocation". The reader gets the allocation; the screen
does not pretend to have computed it.

**Consequence:** criteria 3 and 4 are demoted from "renders as an allocation /
as format specs" to "renders inside a correctly identified section". Doing them
properly needs structured output.

### What would trigger revisiting

- Performance becomes a priority for a production release.
- A specialist reword silently drops the special rendering often enough to
  notice — the brittleness turning out to bite in practice.
- The Creative Brief stage needs to consume placements programmatically rather
  than by reading them (ADR-0016 makes creative depend on the plan's placements;
  today that dependency is satisfied by an agent reading markdown).

Any of those makes structured output the right answer, and the replacement is a
normal refactor of one file plus a contract addition.

## Where the work is

Frontend only. The engine is untouched — that is the point of decision 2.

- [`web/src/app/performance/page.tsx`](../../../web/src/app/performance/page.tsx) — renders every section identically; this is where identification and per-part treatment land.
- [`web/src/lib/deliverable.ts`](../../../web/src/lib/deliverable.ts) — `toSections` stays as it is (it is the only markdown renderer `web/` has, and it has exactly one consumer); its docstring's argument for heading-agnosticism does not.
- [`web/src/lib/deliverable.test.ts`](../../../web/src/lib/deliverable.test.ts) — where the seeded-plan and unmatched-heading specs go.

Deliberately **not** touched, and why:

- `agent-harness/src/marketing_os/governance/pipeline.py` — the stage task already asks the specialist for all four parts. Structured output is deferred.
- `guardrails/performance-plan.md` — already requires all four. If a plan reaches the screen without them, the fix is here or in the reviewer, not in React: see [backfill/06](../../backfill/issues/06-sharpen-guardrail-rubrics.md).

## Comments

**2026-09-04.** Found by a second code-review pass on
[12](archive/12-remaining-screens-wired.md), which noticed the completion note
claimed the criterion outright. The note has been corrected to say **partial**
and to point here, rather than leaving the gap buried in an archived issue.

Worth noting the scope boundary: this is about *reading* a plan, not producing
one. The specialist's own output is governed by its guardrail
(`guardrails/performance-plan.md`), and if that rubric does not already require
the four parts, that is the more upstream fix and probably belongs with
[backfill/06](../../backfill/issues/06-sharpen-guardrail-rubrics.md).

**2026-09-06.** `/grill-with-docs` session resolved the three options into the
[Decision](#decision) section above, and revised the acceptance criteria to match.
No ADR: the choice is cheap to reverse (one file, one consumer, no contract
change), which fails the three-of-three bar. No `CONTEXT.md` change either —
Performance Plan, Placement, KPI tiers and Guardrail are all already defined, and
this decision is about rendering, not the domain. Status moved to
`ready-for-agent`.

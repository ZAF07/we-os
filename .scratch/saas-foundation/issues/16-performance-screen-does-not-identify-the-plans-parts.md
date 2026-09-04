# 16 — The Performance screen shows a plan's sections but cannot tell you which is the channel mix

Status: needs-triage
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

A decision first, because the honest options differ a lot in cost:

- **Have the engine return the plan structured.** The performance specialist
  already decides these four things; if the stage emitted them as fields
  alongside the markdown, the screen would render them directly and the guardrail
  could check them. Most work, and it is the one that makes the missing-KPI-tier
  case detectable. It is also a contract change, so it wants an ADR.
- **Match headings on the frontend.** Cheap — look for "channel", "spend",
  "placement", "KPI" and style those sections specially. Brittle by design: a
  specialist rewording a heading silently drops the special rendering, which is
  the failure mode that is hard to notice.
- **Leave it, and change the criterion.** Defensible if the plan is meant to be
  read as a document. Then [12](archive/12-remaining-screens-wired.md)'s wording
  was wrong rather than the implementation, and this issue closes as `wontfix`
  with that recorded.

The first is the only one that can catch a plan missing its KPI tiers, which is
the argument for it.

## Acceptance criteria

- [ ] The screen identifies the channel mix, the spend allocation, the Placements and the three KPI tiers as those things, not as anonymous sections.
- [ ] A plan missing one of them is visibly incomplete rather than silently shorter.
- [ ] Per-channel spend reads as an allocation of the campaign budget.
- [ ] A spec asserts on a seeded plan containing all four, and on one missing a part.
- [ ] Web gates pass — `pnpm typecheck`, `pnpm lint`, `pnpm format:check`, `pnpm test:unit`.
- [ ] `make test-e2e` still passes.

## Suspected location

- [`web/src/lib/deliverable.ts`](../../../web/src/lib/deliverable.ts) — heading-agnostic by design; the docstring says so explicitly.
- [`web/src/app/performance/page.tsx`](../../../web/src/app/performance/page.tsx) — renders every section identically.
- [`agent-harness/src/marketing_os/governance/pipeline.py`](../../../agent-harness/src/marketing_os/governance/pipeline.py) — the `performance-plan` stage task, if the structured option is taken.
- `guardrails/performance-plan.md` — where "the plan must name all three KPI tiers" would be enforced.

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

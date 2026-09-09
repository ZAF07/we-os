# 01 — The approval-gate spec matches two "Brand strategy" headings and fails under strict mode

Status: ready-for-agent
Type: bug

## Symptom

`make test-e2e` fails `workspace.spec.ts:141` — *approval gate › approving a
stage resumes the run into the next one* — with a Playwright strict-mode
violation:

```
Error: strict mode violation: getByRole('heading', { name: 'Brand strategy' })
resolved to 2 elements:
    1) <h2 class="mt-2.5 mb-[18px] text-xl font-bold tracking-tight">Brand strategy</h2>
    2) <h1 class="mt-5 mb-2 text-[17px] font-bold tracking-tight first:mt-0">Brand Strategy</h1>
```

The two headings are both legitimate and both on screen at the gate:

- `web/src/components/workspace/workspace.tsx:381` — the stage panel's own
  `<h2>Brand strategy</h2>`, the chrome around the deliverable.
- `web/src/components/workspace/deliverable-view.tsx:51` — the `h1` mapping in
  `DeliverableContent`, which renders the deliverable's own leading markdown
  heading. For the brand-strategy stage that document begins `# Brand Strategy`.

Playwright's accessible-name matching is case-insensitive and substring-based by
default, so `'Brand strategy'` matches both spellings.

This is a **defect in the test's locator, not in the product**. Both headings
should be there: the panel names the stage, the document names itself.

## Cause

Commit `2537c9a` ("A stage deliverable is read as a document, not as markdown
source") started rendering deliverable markdown as real HTML via `react-markdown`
instead of dumping it into a `pre-wrap` article. Before it, the document's `#
Brand Strategy` was literal text and matched no heading role; after it, it is an
`<h1>` and the locator became ambiguous.

The spec was not updated with that commit, so the ambiguity shipped latent.

## Why it did not fail every run

It is a race, not a coin flip. The assertion runs immediately after the approve
click; whether it sees one heading or two depends on whether the next stage's
deliverable has rendered yet.

Observed on 2026-09-10 at `d837a3e`:

| Run | Workers | Fixture | Result |
| --- | --- | --- | --- |
| `make test-e2e` | 2 | fresh | **failed** — strict mode violation |
| `pnpm test tests/new-campaign.spec.ts tests/workspace.spec.ts --workers=1` | 1 | reset | passed |

Passing serially is not evidence of health here — a strict-mode violation is
deterministic once both elements are present, so the serial run simply won the
race. Under load it will keep failing.

## Repro

```bash
make test-e2e
```

Fails at `web/tests/workspace.spec.ts:156`. The preserved artifact is
`web/test-results/workspace-approval-gate-ap-*/error-context.md`.

## What's needed

Disambiguate the locator so it names the stage panel's heading and not the
document's. Either is acceptable; prefer whichever reads more clearly beside the
surrounding assertions:

- `{ name: "Brand strategy", exact: true }` — relies on the case difference
  between the panel (`Brand strategy`) and the document (`Brand Strategy`), which
  is real but subtle; or
- scope the query to the stage panel, which states the intent directly and does
  not depend on the deliverable's prose.

Check the sibling assertions in the same spec for the same latent ambiguity —
any `getByRole("heading", ...)` naming a stage is exposed to the same collision
once that stage's deliverable renders.

Do **not** change the product to remove one of the headings. The document
carrying its own title is the point of `2537c9a`.

## Acceptance criteria

- [x] `workspace.spec.ts:141` passes under `make test-e2e` with the default two
      workers, on a fresh stack. (2026-09-10: passed in the full-suite run that
      previously failed it; 71 passed where the baseline had 70.)
- [x] The locator distinguishes the stage panel's heading from the deliverable's
      own, and a comment or the locator's shape makes clear which one is meant.
      (`{ level: 2, name: "Brand strategy" }` — the panel heads the stage at h2,
      `DeliverableContent` maps the document's leading `#` to h1. A comment above
      it says so.)
- [x] Any sibling assertion in `workspace.spec.ts` carrying the same ambiguity is
      fixed with it, or explicitly confirmed as unambiguous.
      (`workspace.spec.ts:110`, the only other stage-heading assertion, is
      unambiguous **by construction**: it asserts "Nothing produced yet" first,
      so no `DeliverableContent` — and so no second heading — is rendered.)
- [x] No product file changes to `workspace.tsx` or `deliverable-view.tsx` for
      this issue — both headings stay. (Diff touches only the spec.)
- [x] Web gates pass — `pnpm typecheck`, `pnpm lint`, `pnpm format:check`,
      `pnpm test:unit`. (All four green; 113 unit tests.)
- [ ] `make test-e2e` passes. **Not satisfied, and deliberately left unticked.**
      The suite is still red: the best run since the fix is 72 passed / 1 failed
      (`calendar.spec.ts:34`), down from 70 / 3 before it. This issue's spec passes in every run since the fix. The
      remaining failure is the pre-existing parallel-load flake — established by
      an A/B against unmodified `main`, see Comments — but the criterion as
      written says the suite passes, and it does not.

## Blocked by

None — can start immediately.

## Comments

**2026-09-10.** Fixed. The full suite went from 70 passed / 3 failed to
71 passed / 2 failed; this issue's spec is among the newly passing.

The two failures that remain are **not** this issue and not issue 02 —
`calendar.spec.ts:34` and `smoke.spec.ts:121`, both on campaign creation. Each
was run in isolation to establish that:

| Spec | Alone, serially, on a reset fixture | In the full suite |
| --- | --- | --- |
| `smoke.spec.ts:121` | passed | failed once, passed twice |
| `calendar.spec.ts:34` | passed on **baseline** (1.8 s) *and* with these changes (2.1 s) | failed every run |

Four full-suite runs, which is what makes the shifting set legible:

| Run | Result | Failed |
| --- | --- | --- |
| baseline, before the fix | 70 passed / 3 failed | `new-campaign:72`, `workspace:114`, `workspace:141` |
| after the fix | 71 / 2 | `calendar:34`, `smoke:121` |
| after the fix | 70 / 3 | `calendar:34`, `campaigns:27`, `workspace:171` |
| after the review fixes | **72 / 1** | `calendar:34` |

None of the three specs these two issues own has failed once since the fix. The
set that does fail rotates across specs neither issue touched, which is the
signature of load, not of a defect. `workspace:171` failed waiting for
`Start run` — a page-load timeout with no heading or segment involved.

`calendar.spec.ts:34` was A/B'd deliberately, by stashing this branch's changes
and running it against unmodified `d837a3e`: it passes either way, so these
changes did not cause it. It fails only when it runs after other
campaign-creating specs have loaded the stack, which is the accumulation pattern
`.scratch/e2e-suite-flake/issues/archive/01` recorded (that same spec failed in
both of its baseline runs) and whose render-time residual issue 03 left open.
No engine error, 401, 402 or 500 appears anywhere in the run — consistent with
render time, not a defect.

That residual is now filed as
[`.scratch/e2e-suite-flake/issues/04`](../../e2e-suite-flake/issues/04-the-suite-still-drops-a-rotating-spec-under-parallel-load.md),
with the four-run table and the A/B, rather than being absorbed here.

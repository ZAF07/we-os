# 02 — A failed save on Back traps the business on the step they were leaving

Status: needs-triage
Type: bug

## Symptom

If the engine is unreachable, a business that clicks **← Back** in the
onboarding wizard cannot go back. The step does not change, the error slot
reads "We could not save your answers. Check your connection.", and every
further Back click fails the same way. Forward is blocked too, so while the
save keeps failing there is no button that moves them anywhere.

Expected: Back should take them back. Going *backwards* to re-read or correct
an earlier answer does not depend on the current step having been written.

Not a crash — the wizard stays responsive and no data is lost. The cost is that
someone on a flaky connection is stuck on one step with no way out but a page
reload, and a reload discards whatever they had typed on that step.

## Repro

Deterministic.

1. `make e2e-up`, sign in as the blank tenant, open `/onboarding`.
2. Fill step 1, click Next to reach step 2.
3. Stop the engine: `docker compose --env-file web/.env.local -f docker-compose.e2e.yml stop engine`
4. Click **← Back**.

The wizard stays on step 2 and shows the save error. It stays there however
many times Back is clicked. Restart the engine and Back works again.

## Suspected location

`web/src/lib/wizard-transition.ts` — `resolveTransition` saves before it moves
in **both** directions, and returns the unchanged step when the save fails:

    if (!(await save())) {
      return { step, attempted: null, finished: false };
    }

    if (direction === "back") {
      return { ...moved, step: Math.max(0, step - 1) };
    }

## How this got here

Introduced deliberately by [01](archive/01-onboarding-spec-depends-on-run-order.md),
which specified it: *"`Back` behaves the same way, so navigation never outruns a
write."* That requirement is sound — the reason it exists is that unawaited
saves were racing each other. What it did not consider is what a business
should be able to do when the save keeps failing.

So this is a gap in the original issue's reasoning, not a defect in its
implementation. Filed rather than fixed in place because choosing the remedy is
a product decision.

## Options for triage

1. **Back never blocks.** Fire the save, move regardless. The answers are still
   in React state and the next successful save writes them, so nothing is lost
   unless the tab is closed. Simplest, and matches what Back means.
2. **Back blocks, but offers an escape** once a save has failed — a "go back
   without saving" affordance in the error slot.
3. **Leave as is.** Defensible if a failed write should always be confronted
   rather than navigated away from, but it needs the error text to say so, and
   to say the answers are still held.

Option 1 is the recommendation: it restores what the control promises, and the
race that motivated the blocking rule was between *concurrent* saves, which the
in-flight guard already prevents on its own.

## Acceptance criteria

- [ ] With the engine unreachable, a business on step 2+ can reach step 1.
- [ ] No answer entered before the failure is lost by going back.
- [ ] Whatever the chosen behaviour, the wizard never presents a state where
      neither Back nor Next moves the business anywhere.
- [ ] A test covers the fixed behaviour, red before and green after.
- [ ] `pnpm typecheck`, `pnpm lint`, `pnpm format:check` and `pnpm test:unit`
      pass in `web/`, and `make test-e2e` passes.

# 02 — A failed segment fetch tells the business owner their Brand DNA is empty, and never retries

Status: ready-for-agent
Type: bug

## Symptom

Step 3 of the new-campaign wizard asks the owner to pick a target audience
segment. The segments are fetched client-side. When that fetch fails, the wizard
renders:

> Your Brand DNA names no audience segments yet. Complete onboarding first.

For an owner whose Brand DNA *does* name segments, every word of that is wrong.
It reports a data problem that does not exist, blames them for it, and sends them
back to redo onboarding they already finished. There is no retry and no way
forward — the wizard is dead until they reload the page, which the message never
suggests.

`web/src/app/(app)/campaigns/new/page.tsx:103-112`:

```ts
useEffect(() => {
  loadAudienceSegments()
    .then(setSegments)
    .catch(() => {
      setSegments([]);
      setFailure(
        "We could not load your audience segments. Refresh to try again.",
      );
    });
}, []);
```

The `catch` sets `segments` to `[]`. Downstream (`page.tsx:256-265`) the render
has three states — `null` is "Loading your segments…", `[]` is the
complete-onboarding message, and a non-empty array is the radio group. Collapsing
a *failure* onto the same `[]` the empty case uses is what produces the wrong
message. A `failure` string is set too, but the empty-state copy is what the eye
lands on next to the field.

Because a campaign cannot be created without a segment, this blocks the primary
job the product exists for.

## How it surfaced

Two e2e specs time out waiting for `getByRole("radio")` — the segment radio that
never appears:

- `new-campaign.spec.ts:72` — *completing the wizard creates a real campaign
  that appears in the list* (fails at `toHaveURL`, still on `/campaigns/new`)
- `workspace.spec.ts:114` — *a draft campaign offers to start a run* (120 s
  timeout in the shared `createCampaign` helper)

Observed 2026-09-10 at `d837a3e`. The trigger that run was a cold Next.js build
cache — `✓ Finished writing to filesystem cache in 68s`, with `/sign-in` taking
24.4 s while it compiled. Under that latency the segment fetch fails, and the
wizard is then permanently wrong. On a warm stack the same specs pass.

This is **not** a recurrence of two already-fixed causes, both of which were
verified fixed and are worth not re-diagnosing:

- `.scratch/e2e-suite-flake/issues/archive/01` — the engine refused session
  tokens 0-5 s past `exp`. Fixed in `3ba1410` by a 10 s verifier leeway.
- `.scratch/e2e-suite-flake/issues/archive/03` — `/campaigns` cost grew with
  campaign count. Fixed in `1534f4e`; 2.53 s → 0.012 s at 120 campaigns.

Issue 01's closing notes anticipated this exact residual: *"plus one 120 s wait
for the wizard's segment radio with no failed engine call behind it."* The tests
are a symptom; the defect is the wizard's handling of a failed fetch.

## Repro

Deterministically, by making the fetch fail — block or fault
`loadAudienceSegments`, or run against a stopped engine:

```bash
make e2e-up
docker stop we-os-e2e-engine-1
# open http://localhost:3100/campaigns/new, advance to step 3
```

The field reads "Your Brand DNA names no audience segments yet" for a tenant
seeded with four segments.

## What's needed

Distinguish "we could not load your segments" from "you have no segments", and
let the owner recover without reloading:

- Keep the failure state separate from the empty state rather than collapsing
  both onto `[]` — e.g. a distinct error state, so the three render branches
  become loading / failed / empty / loaded.
- Say what actually happened, and do not tell an owner with a complete Brand DNA
  to go and complete onboarding.
- Offer a retry that refetches in place. The existing copy already promises
  "Refresh to try again" — a button that does it is better than asking for a
  browser reload, and is what makes the wizard recoverable.
- Consider whether the fetch should retry once on its own before surfacing
  anything, since the observed trigger is transient latency.

The e2e specs should then pass without change — the radios appear because the
fetch succeeds or is retried, not because a test was loosened. If a spec still
needs an explicit wait, add it, but do not paper over a wizard that stays broken.

## Acceptance criteria

- [x] A failed segment fetch renders a message that says the load failed, and
      never tells an owner with segments to complete onboarding.
      (`segmentsFailed` is now its own state, checked before the empty case.
      Copy: "We could not load your audience segments — this is on us, not on
      your Brand DNA.")
- [x] The failure state offers a retry that refetches without a page reload, and
      the wizard proceeds normally once it succeeds. (A "Try again" button calls
      `retrySegments`, which resets to the loading state and refetches.)
- [x] The genuine empty case — a Brand DNA that truly names no segments — still
      says so, and still points at onboarding. (Unchanged `segments.length === 0`
      branch, now reached only when the load actually succeeded.)
- [x] A unit test covers all three states: loaded, genuinely empty, and failed
      (asserting the failed state does not carry the onboarding copy).
      (`web/src/app/(app)/campaigns/new/page.test.tsx` — five tests: loaded,
      genuinely empty, failed, the automatic single retry, and recovery via the
      button. The failed case asserts the onboarding copy is absent.)
- [x] `new-campaign.spec.ts:72` and `workspace.spec.ts:114` pass under
      `make test-e2e` with the default two workers. (2026-09-10: both passed in
      the full-suite run that previously failed them.)
- [x] Web gates pass — `pnpm typecheck`, `pnpm lint`, `pnpm format:check`,
      `pnpm test:unit`. (All four green; 113 unit tests, up from 108.)
- [ ] `make test-e2e` passes. **Not satisfied, and deliberately left unticked.**
      The suite is still red: the best run since the fix is 72 passed / 1 failed
      (`calendar.spec.ts:34`), down from 70 / 3 before it. Both of this issue's specs pass in every run since the fix. The
      remaining failure is the pre-existing parallel-load flake — established by
      an A/B against unmodified `main`, see Comments — but the criterion as
      written says the suite passes, and it does not.

## Blocked by

None — can start immediately. Independent of
[01](01-approval-gate-spec-matches-two-brand-strategy-headings.md); the two touch
different files.

## Comments

**2026-09-10.** Fixed. Both named specs pass in the full suite that previously
failed them, and the wizard now distinguishes a failed load from an empty Brand
DNA.

Two things went slightly beyond the brief, both while making the fix hold:

- **The load now cancels.** `startSegmentLoad` returns a teardown that abandons
  an in-flight load, so its answer cannot land on a field nobody is waiting on.
- **The wizard-level `failure` banner is no longer set for this case.** The
  message belongs next to the field it concerns, with the retry beside it, rather
  than in the shell's error slot. The banner still carries submit failures.

The suite's two remaining failures are neither this issue nor 01 — see the
Comments on [01](01-approval-gate-spec-matches-two-brand-strategy-headings.md)
for the isolation runs that establish it, including an A/B of `calendar.spec.ts`
against unmodified `d837a3e`.

The suite's residual flake is filed as
[`.scratch/e2e-suite-flake/issues/04`](../../e2e-suite-flake/issues/04-the-suite-still-drops-a-rotating-spec-under-parallel-load.md).

**Same shape elsewhere, deliberately left alone.** `web/src/app/(app)/campaigns/page.tsx:28`
and `web/src/app/(app)/onboarding/page.tsx:104` both answer a failed load with
"Refresh to try again" and no retry button. Neither collapses a failure onto a
misleading empty state, so neither is this bug — but the recovery is as poor.
Worth a follow-up issue; out of scope here.

### Code review, 2026-09-10

Both review axes independently caught the same real defect in the first cut, and
they were right: `retrySegments` called `fetchSegments()` and **dropped the
returned teardown**, so only the mount ever wired cancellation up. The comment
claimed a retry could supersede an earlier attempt; the code could not do it.

Fixed by holding the live canceller in a ref — `retrySegments` now invokes the
previous one before starting the next. The function is renamed
`fetchSegments` → `startSegmentLoad`, which is what it actually does: it starts a
load and hands back the way to abandon it. Standards flagged the old name as
misleading for exactly the reason the bug happened.

Also from review: the `for (const attempt of [1, 2])` loop was a general N-attempt
construct expressing one retry, with a magic `2` in two places. Replaced with a
plain try / retry-once / give-up nest. And the duplicated mock-arming block in
the tests is now one `failsOneWholeLoad` helper.

**The double-retry test both reviews asked for was written, and it disproved its
own premise.** Instrumenting it showed only one call reaching the mock after two
clicks: the moment a retry starts, the field returns to its loading state and the
"Try again" button unmounts, so a person cannot start a second retry on top of
the first. Two loads racing to answer this field is not reachable through the UI.
The test that shipped asserts that invariant instead — the button is gone while a
retry is in flight — which is the honest guarantee and the one worth locking
down. The ref is still correct for the mount-teardown path.

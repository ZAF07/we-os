# 01 — Two concurrent saves race on Finish, so the wizard can restore a stale answer

Status: ready-for-agent
Type: bug

## Symptom

`make test-e2e` fails on
`onboarding.spec.ts:106` — "completing the questionnaire lands on the Brand
screen with the answers" — roughly **two runs in three**, at:

    await expect(page.getByText(businessName)).toBeVisible();   // "Peakline Roasters"

The Brand screen shows **"Acme Coffee"** instead. Everything else on the screen
is correct: every other field carries this spec's answers.

## Cause

Not spec ordering. The wizard opens on step 0 unconditionally
(`useWizard` is `useState(0)`, `web/src/components/wizard/use-wizard.ts:27`), so
there is no resume to depend on, and the spec's four `Next` clicks from step 0
do reach step 5. The earlier diagnosis on this issue — that the spec fills only
four of five steps and relies on an earlier spec having saved step 1 — was
wrong.

The defect is that **Finish issues two concurrent saves**.

`onNext` fires a save it does not await:

    onNext={() => {
      if (!stepIncomplete(step)) void persist();   // page.tsx:179
      next();
    }}

On the final step `next()` calls `onFinish`, which fires its own:

    onFinish: () => {
      void persist().then(() => router.push("/brand"));   // page.tsx:122-123
    }

Both POST the **whole** answers map (`toAnswerPayload(answers)`,
`page.tsx:108`), and both are built from a React state snapshot captured when
their handler ran. The two requests hit `POST /brand-dna/answers` in whatever
order the network delivers them, and the engine's `upsert` merges each over
what is stored — so the request processed **last** wins.

When the staler payload lands second it overwrites the fresher one, restoring
the value saved before the final edits. That is the "Acme Coffee" symptom: step
1 reverts to the previously stored answer, while every other field — which had
no prior stored value to revert to — keeps this spec's answer.

Intermittent because it is a genuine race between two in-flight POSTs. Under
Playwright's synthetic clicks they fire microseconds apart and ordering is near
random; a human clicking Finish gives the first write time to land, which is
why this was never hit by hand.

## Confirmed in the database after a failing run

    ten_e2eblank... | q_business_name    | Acme Coffee          <- the earlier stored value
    ten_e2eblank... | q_what_they_sell   | Specialty coffee kits and subscriptions
    ten_e2eblank... | q_geography        | Australia-wide, online only
    ...every other field is this spec's own answer.

## Not a regression

Measured, because it kept correlating with unrelated work. Three clean full
`make test-e2e` runs on the branch and three on its parent commit, each with
`docker compose down -v` between:

| | run 1 | run 2 | run 3 |
| --- | --- | --- | --- |
| branch | fail | pass | fail |
| parent | fail | pass | fail |

Same assertion, same cause, same rate.

First seen during [remove-cli-runner/01](../../remove-cli-runner/issues/archive/01-remove-the-campaign-driving-cli.md),
which recorded it as a one-off; it is not one.

## What the product should do

One save per transition, awaited before anything else happens.

- `Next` awaits the save with the button **disabled** while it is in flight, and
  advances only once it resolves. A failed save surfaces in the wizard's
  existing error slot and the step does not change.
- `Back` behaves the same way, so navigation never outruns a write.
- Finish saves **once** and navigates to `/brand` only on success. The
  fire-and-forget save in `onNext` goes away.

Blocking is deliberate: it is one small POST, and optimistic advance is what
produced this bug. Silent data loss is worse here than a short pause, and
"saved as you go" is a promise the wizard's own progress note already makes.

Blank handling is **unchanged**. `toAnswerPayload` filtering out blanks is
correct — a question the business has not answered yet must not be sent to the
engine as an empty answer. Removing an existing answer is a separate operation,
tracked in
[brand-dna-crud/01](../../brand-dna-crud/issues/01-tenants-cannot-delete-a-brand-dna-answer.md).

## Scope

Wizard only. Campaign creation (`web/src/app/campaigns/new/page.tsx`) already
requires every field, blocks advancing on any blank, and submits the goal once
at the end — no partial saves, no merge, nothing blank on the wire. It needs no
change.

## Correction — the cause above is also wrong

The concurrent-save diagnosis was measured and fixed, and it was a real defect.
It was **not** what makes this spec flake. Probes on a failing run showed:

    PROBE load    {"question_id":"q_business_name","answer":"Acme Coffee"}
    PROBE field value before click: Acme Coffee
    PROBE persist {"question_id":"q_business_name","answer":"Acme Coffee"} size 4

The *first* save already carries the stale name, and every row in
`dna_answers` shares one `updated_at` — one write per step, no race left. The
same probe on a passing run reads `Peakline Roasters` at all three points.

The field itself holds the wrong value **before anything is saved**. The
wizard's inputs are controlled by React state, so a Playwright `fill()` that
lands before the page is interactive sets the DOM value and is then discarded
by the next render. The field snaps back to what was loaded — which for a
question the business has answered before is the previous answer, and for the
rest is blank, so their later fills stick. That is exactly why only
`q_business_name` was ever wrong.

Fixed in the spec: each fill is retried until the value holds
(`fillAndConfirm`), so the spec asserts its own answers rather than a stale one
that happens to still be there.

## Acceptance criteria

- [x] Finish issues exactly one `POST /brand-dna/answers`, not two.
- [x] `Next`, `Back` and Finish await their save; the primary button is disabled
      while it is in flight.
- [x] A save that fails leaves the wizard on its current step and shows the
      error, rather than advancing.
- [x] A question the business has not answered is still absent from the payload
      — no empty-string answers are sent.
- [x] `make test-e2e` passes on three consecutive clean runs.
- [x] The spec does not depend on any other spec having run first.

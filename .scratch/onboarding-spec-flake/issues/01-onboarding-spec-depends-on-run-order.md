# 01 — The onboarding e2e spec fails ~2 runs in 3, depending on spec order

Status: needs-triage
Type: bug

## What happens

`make test-e2e` fails on
`onboarding.spec.ts:106` — "completing the questionnaire lands on the Brand
screen with the answers" — roughly **two runs in three**, at:

    await expect(page.getByText(businessName)).toBeVisible();   // "Peakline Roasters"

The Brand screen shows **"Acme Coffee"** instead. Everything else on the screen
is correct: every other field carries this spec's answers.

## Why

The wizard has **five** steps (one per question section: Business, Customers,
Differentiation, Reach & constraints, Recommended). The spec's fill loop runs
four:

    for (let step = 1; step <= 4; step += 1) { ...; await page.getByRole("button", { name: "Next →" }).click(); }

So it depends on the earlier spec — "answers save partway and are still there on
return" (`:83`) — having already saved step 1, and on the wizard resuming past
it. When that resume does not happen, step 1 is never filled by this spec and
`q_business_name` keeps the earlier spec's value.

Confirmed in the database after a failing run:

    ten_e2eblank... | q_business_name    | Acme Coffee          <- the earlier spec's
    ten_e2eblank... | q_what_they_sell   | Specialty coffee kits and subscriptions
    ten_e2eblank... | q_geography        | Australia-wide, online only
    ...every other field is this spec's own answer.

The spec's own comments at `:104` and `:110-115` already document the coupling.

## Not a regression

Measured, because it kept correlating with unrelated work. Three clean full
`make test-e2e` runs on the branch and three on its parent commit, each with
`docker compose down -v` between:

| | run 1 | run 2 | run 3 |
| --- | --- | --- | --- |
| branch | fail | pass | fail |
| parent | fail | pass | fail |

Same assertion, same cause, same rate. It passes reliably against a clean
tenant (`--grep "completing the questionnaire"` on a fresh volume).

First seen during [remove-cli-runner/01](../../remove-cli-runner/issues/archive/01-remove-the-campaign-driving-cli.md),
which recorded it as a one-off; it is not one.

## Fix direction

Make the spec independent of what ran before it, rather than making the ordering
more reliable — a spec that depends on another spec's writes will keep finding
new ways to fail. Either fill all five steps unconditionally, or give this spec
its own tenant so no earlier answer is there to survive.

## Acceptance criteria

- [ ] `make test-e2e` passes on three consecutive clean runs.
- [ ] The spec does not depend on any other spec having run first.

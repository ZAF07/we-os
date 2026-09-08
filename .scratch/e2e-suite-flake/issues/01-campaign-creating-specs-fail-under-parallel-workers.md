# 01 — The e2e suite fails a shifting handful of campaign-creating specs under parallel workers

Status: needs-triage
Type: bug

## Symptom

`make test-e2e` fails roughly three specs per run, and **which** specs fail
changes every run. The suite is the repo's only pre-push gate for the web app
(`CLAUDE.md`, "Before pushing"), so a red run carries no signal: there is no way
to tell a real regression from the usual noise without rerunning by hand.

Four runs on 2026-09-08, two on `345ebbb` (before the credits rename) and two on
`1ebf441` (after it):

| Run | Workers | Result | Failed |
| --- | --- | --- | --- |
| `345ebbb`, `make test-e2e` | 2 | 45 passed, 3 failed | `calendar.spec.ts:34`, `new-campaign.spec.ts:61`, `new-campaign.spec.ts:105` |
| `1ebf441`, `make test-e2e` | 2 | 45 passed, 3 failed | `calendar.spec.ts:34`, `campaigns.spec.ts:27`, `home.spec.ts:64` |
| `1ebf441`, `pnpm test --workers=1` | 1 | 47 passed, 1 failed | `home.spec.ts:29` |
| `1ebf441`, the three specs from run 2, `--workers=1` | 1 | 13 passed | — |

The failure count is the same before and after an unrelated change, and every
test that failed in one run passed on rerun. `home.spec.ts:29` failed in the
serial full-suite run and then passed when that file was run alone.

The visible failures are all timeouts inside the new-campaign wizard or on an
assertion about what the campaign list now contains — e.g.

    Locator: getByText('Nothing is waiting on a decision')
    Expected: visible ... element(s) not found      (home.spec.ts:71)

    await page.getByLabel("Campaign budget").fill("1000");   (home.spec.ts:42)

## Repro

    make test-e2e

Not deterministic — expect a different two or three specs to fail each time.
Reducing to one worker lowers the failure count but does not reach zero:

    make e2e-up
    cd web && E2E_STACK=compose pnpm test --workers=1

Running a single spec file on its own has passed every time tried.

## Suspected location

Not diagnosed — `/diagnosing-bugs` should confirm before anything is changed.
What is established:

- Six specs create campaigns through the same wizard against the same seeded
  tenant: `calendar`, `campaigns`, `home`, `new-campaign`, `smoke`, `workspace`.
- `uniqueName` (`web/tests/fixtures.ts:34`) keeps campaign *names* from
  colliding, but nothing scopes the *tenant*, and there is no per-test cleanup —
  no `afterEach`/`afterAll` in any spec, no global teardown in
  `web/playwright.config.ts`. Campaigns accumulate for the life of the stack.
- So assertions phrased over tenant-wide state ("nothing is waiting on a
  decision", "leaves the active list") are answered by whatever every other
  spec has left behind.
- `workers: 2` (`web/playwright.config.ts:33`) is deliberate and documented as a
  throughput choice, so the contention is expected to be survivable; it is not.

Worth weighing: whether each test should get its own tenant (the stack already
seeds two — see `E2E_CLERK_ORG_ID` / `E2E_CLERK_BLANK_ORG_ID`), whether the
tenant-wide assertions should be scoped to the campaign the test created, or
whether creation should be seeded through the API rather than driven through the
wizard in every spec that merely needs a campaign to exist.

## Acceptance criteria

- [ ] `make test-e2e` passes on an unchanged checkout, ten runs in a row.
- [ ] Assertions about "the list" or "the queue" are scoped to state the test
      itself created, or the test owns a tenant nothing else writes to.
- [ ] The suite still passes with `workers: 2` — the fix is isolation, not
      serialising the suite to hide the contention.
- [ ] `pnpm typecheck`, `pnpm lint`, `pnpm format:check` and `pnpm test:unit`
      pass in web.

## Comments

Filed 2026-09-08 while closing out `.scratch/credits-rename`. The credits work
touched exactly one line of one spec (`home.spec.ts:18`, the "Allowance" →
"Credits" label) and that assertion passed in all four runs above; this bug is
older than that change and is filed separately rather than fixed inside it.

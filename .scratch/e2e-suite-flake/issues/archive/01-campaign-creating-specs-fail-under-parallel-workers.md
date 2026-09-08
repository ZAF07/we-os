# 01 — The e2e suite fails a shifting handful of campaign-creating specs under parallel workers

Status: completed
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

- [x] `make test-e2e` passes on an unchanged checkout, ten runs in a row.
      (2026-09-09, fixed engine: 10/10 fresh-stack runs, 60 passed each.)
- ~~Assertions about "the list" or "the queue" are scoped to state the test
  itself created, or the test owns a tenant nothing else writes to.~~
  Withdrawn: this prescribed a fix for shared tenant state, which the
  diagnosis ruled out as the cause. No spec was changed.
- [x] The suite still passes with `workers: 2` — the fix is isolation, not
      serialising the suite to hide the contention. (`workers: 2` unchanged;
      the fix is in the engine's token verifier. On a stack seeded to 120+
      campaigns the two-worker suite still drops a spec or two, but to render
      time, never to a 401 — see the last evidence block and issue 03.)
- [x] `pnpm typecheck`, `pnpm lint`, `pnpm format:check` and `pnpm test:unit`
      pass in web. (Run after review even though no web file changed: all
      four green, 72 unit tests.)

## Comments

Filed 2026-09-08 while closing out `.scratch/credits-rename`. The credits work
touched exactly one line of one spec (`home.spec.ts:18`, the "Allowance" →
"Credits" label) and that assertion passed in all four runs above; this bug is
older than that change and is filed separately rather than fixed inside it.

Seen again 2026-09-08 while closing out `.scratch/landing-and-pricing`, which
touched no campaign code. On a freshly started stack the full suite passed 58
of 59 (`new-campaign.spec.ts:105` failed, then passed alone). After five suite
runs against the same stack, a run of the `chromium` and `chromium-public`
projects failed `new-campaign.spec.ts:61`, `smoke.spec.ts:94` and
`workspace.spec.ts:43`, all at the "Create campaign" step. The failure set
grows with the number of campaigns the stack has accumulated, which supports
the isolation reading above. The new `chromium-public` project, which creates
nothing, has not failed once.

### Diagnosis (2026-09-09, `/diagnosing-bugs`)

**Confirmed cause: the engine refused session tokens 0-5 s past `exp`; the
web app forwards exactly those.** Not tenant-wide state, not worker
contention. Campaign accumulation only mattered because it made runs slower,
which made more of them straddle a token boundary.

Mechanism, verified at every layer:

- A Clerk session token lives 60 s. Every test context starts from the
  token `auth.setup` saved, and pages minted more along the way.
- `clerkMiddleware` judges a token valid up to 5 s past `exp`
  (`DEFAULT_CLOCK_SKEW_IN_MS = 5000` in `@clerk/backend`) and
  `auth().getToken()` with no template returns that raw token, so the BFF
  forwards a token up to 5 s expired. Past 5 s it handshakes and mints a new
  one instead.
- The engine verified with PyJWT's default `leeway=0`, so every token had a
  5 s window, 60 s after mint, in which the web app trusted it and the
  engine answered 401 "Sign in to continue." Whichever specs called the
  engine in that window failed - hence a *shifting* handful, and hence
  `chromium-public` never failing.
- What the failures look like from the specs: the create action returns
  `{"campaign":null,"error":"Sign in to continue."}` so the wizard stays on
  `/campaigns/new` ("Create campaign" step timeouts); `loadAudienceSegments`
  throws so no radio ever renders (the `getByRole("radio")` /
  "Campaign budget" 120 s timeouts); Home/Workspace render the engine-error
  state instead of the queue or "Campaign not found".

Evidence: with the engine's verifier instrumented, every 401 across 12 suite
runs against one stack was `ExpiredSignatureError` with `exp-now` in
`{0,-1,-2,-3,-4}` and nothing else; Playwright traces of two failing specs
show the server-action responses carrying the message. A deterministic
probe (one minted token reused at a chosen age against `/campaigns/<unknown>`)
FAILS at 62 s and PASSES at 30 s and 70 s on the unfixed engine, and PASSES at
62 s and 64 s on the fixed one.

Hypotheses ranked before instrumenting, for the record: (1) engine rejects
near-expiry tokens the BFF still trusts - **confirmed**; (2) clock skew
between host and the Docker VM - ruled out, clocks agree within 100 ms;
(3) `GET /campaigns` growing O(n) with sync DB calls starving the engine -
real (suite 43 s at 12 campaigns, 231 s at 118) but only a slowdown, never a
timeout on its own; (4) `count()`/`isVisible()` races on Home and Calendar -
ruled out, those pages render fully server-side before `goto` resolves;
(5) Clerk dev-instance rate limiting - not observed.

Fix: `_CLOCK_SKEW_LEEWAY_SECONDS = 10` passed as `leeway` in
`JwksTokenVerifier.verify` (`agent-harness/src/marketing_os/adapters/auth.py`),
matching the 10 s Clerk itself dates `nbf` before `iat`. Regression tests in
`agent-harness/tests/test_auth.py`: a token 5 s past `exp` (the most the BFF
forwards) verifies; one 15 s past `exp` is refused; a token whose `iat` is 3 s
ahead verifies. The pre-existing 60 s-expired rejection test still passes.
The contract is recorded as an amendment to ADR-0013.

Left open, seen once in 12 runs (run 11, 118 campaigns accumulated): two
plain `page.goto` calls hung for the full 120 s with no matching web-log
entry, consistent with a slow handshake round trip to Clerk's dev instance
rather than with anything in this repo. Watch for it in the acceptance runs.

### Acceptance evidence (2026-09-09)

Before the fix, against one stack with 2 workers: runs 1-6 (up to 60
campaigns, 43-58 s each) green; runs 7, 9, 11, 12 (72-130 campaigns,
97-231 s each) failed 2-4 specs, every one traced to a 401 in the 0-5 s
window. After the fix (`make check`: 591 passed; `make test-postgres`: 684
passed):

- `make test-e2e`, fresh stack each time: 10/10 runs, 60 passed each.
- one reused stack, `--workers=1 --trace on` so each run lasts 98-110 s and
  crosses the window mid-run: 4/4 runs, 53 passed each; 0 engine 401s in
  5,358 requests over that stack's life.
- deterministic probe: token aged 62 s and 64 s now verifies.

The 120 s `page.goto` hangs seen once pre-fix (run 11) did not recur in any
of the 18 post-fix runs.

After code review, the failing shape itself — one reused stack, `workers: 2`,
runs long enough to cross the window — was rerun on a stack seeded to 124
campaigns through the engine API: three runs of 191 s, 86 s and 90 s, with
3, 1 and 0 specs failing and **0 engine 401s in the stack's whole life**
(before the fix, every run of that length carried a burst of them). The four
failures were all render time at 126-138 campaigns: Calendar and Home take
3-5 s to answer, so the 5 s expectations in the nav-rail and Workspace specs
time out, plus one 120 s wait for the wizard's segment radio with no failed
engine call behind it. That is the O(n) list cost, filed as issue 03; a fresh
`make test-e2e` stack starts at zero campaigns and never reaches it.

## Completion

- Completed: 2026-09-09
- Commit: <to be filled in manually>

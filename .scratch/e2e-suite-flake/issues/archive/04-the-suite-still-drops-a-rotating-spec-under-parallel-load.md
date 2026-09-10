# 04 — The e2e suite still drops a rotating spec or two under parallel load

Status: completed
Type: bug

## Symptom

`make test-e2e` fails one to three specs per run on a freshly built stack, and
**which** specs fail changes every run. The suite is the repo's only pre-push
gate for the web app (`CLAUDE.md`, "Before pushing"), so a red run still carries
no signal: there is no way to tell a real regression from the usual noise without
rerunning specs by hand.

This is the **residual** left by the two causes that were found and fixed, not a
recurrence of either. Both are genuinely gone:

- [01](archive/01-campaign-creating-specs-fail-under-parallel-workers.md) — the
  engine refused session tokens 0-5 s past `exp`. Fixed in `3ba1410` (10 s
  verifier leeway). **No engine 401, 402 or 500 appears anywhere in the runs
  below.**
- [03](archive/03-keep-the-campaign-list-fast-as-campaigns-grow.md) — `/campaigns`
  cost grew with campaign count. Fixed in `1534f4e`; 2.53 s → 0.012 s at 120
  campaigns.

01's closing notes named this residual precisely, and 03 left it open:

> The four failures were all render time at 126-138 campaigns: Calendar and Home
> take 3-5 s to answer, so the 5 s expectations in the nav-rail and Workspace
> specs time out, plus one 120 s wait for the wizard's segment radio with no
> failed engine call behind it.

It has now been rediscovered three times across separate sessions. Filing it so
the diagnosis is not paid for a fourth time.

## Repro

```bash
make test-e2e
```

Not deterministic — expect a different one to three specs to fail each run.

Four runs on 2026-09-10, at `d837a3e` and on the branch for
`.scratch/workspace-gate-defects` (which fixed two *unrelated* defects that the
same suite had surfaced):

| Run | Result | Failed |
| --- | --- | --- |
| `d837a3e`, before that branch | 70 passed / 3 failed | `new-campaign:72`, `workspace:114`, `workspace:141` |
| with the branch | 71 / 2 | `calendar:34`, `smoke:121` |
| with the branch | 70 / 3 | `calendar:34`, `campaigns:27`, `workspace:171` |
| with the branch, after review fixes | 72 / 1 | `calendar:34` |

The first run's three failures were real defects with real causes, fixed on that
branch and green ever since. Every failure in rows 2-4 is this bug.

## What is established

Run in isolation, on a fixture reset with `make e2e-test-reset` and one worker,
the failing specs pass:

| Spec | Alone, serially | In the full suite |
| --- | --- | --- |
| `smoke.spec.ts:121` | passed | failed once, passed twice |
| `calendar.spec.ts:34` | passed | failed all three runs |

`calendar.spec.ts:34` was **A/B'd against unmodified `main`** — stash the branch,
`make e2e-test-reset`, run the spec, restore, reset, run again. It passes both
ways (1.8 s on baseline, 2.1 s with the branch), so nothing on that branch causes
it. It fails only when it runs *after* other campaign-creating specs.

Failure shapes seen, none with a failed engine call behind them:

- `calendar.spec.ts:51` — `getByRole('navigation', { name: 'Stages' })` not
  visible within the default 5 s, immediately after clicking "Create campaign".
  The test has no explicit wait; creation takes ~2-6 s depending on load.
- `smoke.spec.ts:145` — `toHaveURL(/\/campaigns\/smoke-campaign/)` still on
  `/campaigns/new` after "Create campaign", 14 polls over 5 s.
- `workspace.spec.ts:171` — 120 s timeout waiting for the `Start run` button, a
  plain page-load stall.

Also observed, and possibly the trigger rather than a separate fact: on one run
the web container spent 68 s rebuilding its Next.js filesystem cache
(`✓ Finished writing to filesystem cache in 68s`), with `/sign-in` taking 24.4 s
while it compiled. The two specs that failed that run were the two whose fixtures
were being created during that window.

A React hydration mismatch on Clerk's `UserButton` (`AppLayout`,
`src/app/(app)/layout.tsx:28`) logs on most runs. It does not fail a test and may
be unrelated, but it is noise in the same window and worth ruling in or out.

## Not yet established

Deliberately not diagnosed here — that is `/diagnosing-bugs`' job. Open
questions worth starting from:

- Is this purely **assertion timeouts too tight for a loaded stack** (the 5 s
  default against a 2-6 s create), in which case the fix is explicit waits at the
  create-campaign step rather than anything in the product?
- Or is there still a **real slowdown** under two workers that 03's fix did not
  reach — 03 fixed the list read, but creation and the Workspace render were not
  measured the same way.
- Does the Next.js cache rebuild account for the worst runs, and if so should the
  stack be warmed (a first request per route) before the suite starts?
- `workspace.spec.ts:171`'s 120 s stall is a different magnitude from the 5 s
  assertion failures and may be a second bug wearing the same costume.

## Suspected location

No single site. The specs that fail all drive campaign creation through the
wizard: `calendar.spec.ts:34`, `smoke.spec.ts:121`, `campaigns.spec.ts:27`,
`workspace.spec.ts:114`/`171`, `new-campaign.spec.ts:72`. `web/playwright.config.ts`
sets `workers: 2` and a 120 s per-test timeout with `retries: 0` locally.

## Acceptance criteria

- [x] `make test-e2e` passes on an unchanged checkout, ten runs in a row.
      (2026-09-10: 10/10 fresh-stack runs, 73 passed each, 73-80 s; then
      `make test-e2e` itself, 73 passed — see the acceptance evidence below.)
- [x] The fix is isolation or an honest wait, not `workers: 1` and not a blanket
      timeout raise — serialising the suite hides the contention rather than
      resolving it, and 01 rejected that for the same reason. (`workers: 2` and
      every timeout unchanged. The fixes remove the causes: the route is
      compiled before the suite, the cache write no longer happens, sleep is
      held off, sessions renew themselves, and the nav rail hydrates cleanly.)
- [x] Whatever the cause turns out to be, it is recorded in this file so a fourth
      rediscovery is unnecessary. (Five causes, each with its evidence, under
      Diagnosis below.)
- [x] `make check` and `make test-postgres` pass. (650 passed / 760 passed.)
- [x] Web gates pass — `pnpm typecheck`, `pnpm lint`, `pnpm format:check`,
      `pnpm test:unit`. (All clean; 115 unit tests.)

## Blocked by

None — can start immediately.

## Comments

### Diagnosis (2026-09-10, `/diagnosing-bugs`)

**There was no single residual. Five separate things were making the suite
drop specs, and every one of them was rarer or absent on a reused stack —
which is why each diagnosis on a reused stack found nothing, and the next
`make test-e2e` failed again.** In order of how many failures each caused:

1. **The Workspace route was compiled on demand, mid-suite, under load.**
   The setup project warms six routes so no spec pays a first compile, but
   `/campaigns/[slug]` — where every campaign-creating spec lands right after
   "Create campaign", inside a 5 s assertion — was never on the list, and it
   is the heaviest route there is (its client bundle carries the markdown
   renderer). The first spec to reach it paid the compile: 2.3 s on a warm
   machine, ~10 s on a cold one (`○ Compiling /campaigns/[slug] ...` at
   05:45:18.9, first Workspace page served at 05:45:30.0 in a cold run, and
   both failures that run sat inside that window). Which spec paid depended on
   scheduling, hence the rotation. `smoke:121`, `calendar:34`, `campaigns:27`,
   `new-campaign:72`, `workspace:*` were all this. Fixed by warming a
   not-found slug of that route (and the run stream route) in
   `web/tests/auth.setup.ts`.

2. **Turbopack's persistent filesystem cache was written mid-suite.** Next 16
   turns it on for `next dev`; in the e2e container it writes ~460 MB into an
   anonymous volume that dies with the stack, and the write stalls the dev
   server: `✓ Finished writing to filesystem cache in 31.5s` overlapped a
   `GET /home 200 in 6.9s` and BFF fetches of 3-4 s while the engine answered
   in 50 ms. The issue's worst run (a 68 s write, `/sign-in` at 24 s) was this.
   Fixed by `DEV_FILESYSTEM_CACHE=0` in `docker-compose.e2e.yml`, read by
   `web/next.config.ts`.

3. **The laptop went to sleep.** On battery macOS idle-sleeps a minute after
   the display dims, and a suite run is not user activity. `pmset -g log`:
   "Entering Sleep state due to 'Idle Sleep'" at 13:55:28, wake at 14:04:08;
   the run in progress showed two tests at 520 s (Playwright's 120 s timeout
   could not fire either), `ERR_NETWORK_IO_SUSPENDED` and `ChunkLoadError`.
   This is the "120 s page.goto with no matching web-log entry" that 01 left
   open and the `workspace:171` stall in this issue. Fixed by wrapping
   `make test-e2e` in `caffeinate -i` where the binary exists.

4. **Every spec started from a session token saved at the beginning of the
   run, and the token lives 60 s.** A spec starting later than that began with
   an expired token. A page navigation renews one through Clerk's handshake,
   but a server action or client-side route change cannot: the middleware
   refuses any non-GET request more than 5 s past expiry
   (`session-token-expired-refresh-non-eligible-non-get`, captured with the
   proxy instrumented), and the page reports a failed action rather than a
   sign-in. Captured exactly once in ~1,100 tests: a wizard page loaded 4 s
   past expiry (inside the leeway, so no handshake), its first action fired
   5 s past it, the built-in retry hit the same token 300 ms later, and the
   spec waited 120 s for a segment radio with no engine call behind it — the
   shape this issue could not place. Slower runs push more specs past the
   60 s mark, which is why every slowdown in the suite's history made this
   worse. Fixed by saving the sessions without their `__session` cookie
   (`web/tests/session-state.ts`): each spec's first navigation is renewed by
   the handshake and runs on a token minted for it. A related product defect
   fixed alongside: `proxy.ts` passed `request.url` as the sign-in return
   URL, which under `next dev --hostname 0.0.0.0` carries `0.0.0.0:3000`;
   Clerk refuses that origin and sends the person to Home instead of back, so
   a transient miss became a spec on the wrong screen. The return URL is now
   a path.

5. **A React hydration mismatch in the nav rail reset client state under a
   click.** `UserButton` renders its fallback until Clerk's script loads and
   its host once it has; the server always serialises the fallback, but on a
   slow dev server the script can finish before React hydrates, so the client
   hydrates the host against fallback markup. React answers by discarding the
   server tree and re-rendering on the client — every component's state
   resets, a wizard goes back to step 1, and a click in that window is lost.
   Seen as a run where the server received *nothing* for 6 s after "Create
   campaign" was clicked, with only the hydration error in the log. The issue
   had filed this error as noise. Fixed in `app-shell.tsx` by rendering the
   fallback until mounted (`useSyncExternalStore`), with a unit test that
   server-renders `UserCard`, hydrates it with Clerk "already loaded", and
   asserts React reports no recoverable error — red before the fix, green
   after.

Ruled out, with evidence: the engine's synchronous store calls do block its
event loop (max stall 702 ms, no handler over 1 s) — a contributor to load,
never a 5 s failure; Clerk dev-instance latency (token refreshes of 1-2 s,
one 2.1 s middleware call) — same; the engine never answered 401/402/500 in
any run, so 01's fix holds.

Hypotheses ranked before instrumenting: (1) on-demand compile of the
Workspace route — confirmed; (2) fresh-stack IO churn (volume recreation, cold
page cache) making that compile slower — confirmed as the amplifier, not a
cause on its own; (3) the filesystem-cache write — confirmed; (4) Clerk round
trips — contributor only; (5) engine event-loop blocking — ruled out. Causes 3,
4 and 5 above were not on the list: they were found by instrumenting the
proxy and reading the power log, which is the argument for instrumenting
before theorising.

Evidence lives in the run logs of the session; the tools used were: a run loop
(`make e2e-down && make e2e-up` before each run to match `make test-e2e`, a
custom Playwright reporter for per-action timings, both containers' logs per
run), a summariser over them, and a probe that measures the click-to-Workspace
wait with and without the route warmed (3.3 s vs 0.8 s under load on a cold
container).

### Acceptance evidence (2026-09-10)

Ten `make test-e2e`-equivalent runs in a row on the final code — `make
e2e-down && make e2e-up` before each, so every run starts on a fresh stack
with a cold Turbopack cache, exactly as `make test-e2e` does — all green,
under `caffeinate`:

| Run | Result | Seconds | Create → Workspace wait (max / median) | Sign-in bounces | Workspace compiles mid-run | Cache writes |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 73 passed | 73 | 793 ms / 294 ms | 0 | 0 | 0 |
| 2 | 73 passed | 75 | 1810 ms / 288 ms | 0 | 0 | 0 |
| 3 | 73 passed | 78 | 813 ms / 786 ms | 0 | 0 | 0 |
| 4 | 73 passed | 73 | 806 ms / 285 ms | 0 | 0 | 0 |
| 5 | 73 passed | 80 | 813 ms / 290 ms | 0 | 0 | 0 |
| 6 | 73 passed | 75 | 799 ms / 287 ms | 0 | 0 | 0 |
| 7 | 73 passed | 79 | 799 ms / 786 ms | 0 | 0 | 0 |
| 8 | 73 passed | 75 | 813 ms / 291 ms | 0 | 0 | 0 |
| 9 | 73 passed | 77 | 808 ms / 293 ms | 0 | 0 | 0 |
| 10 | 73 passed | 76 | 821 ms / 312 ms | 0 | 0 | 0 |

Before the fixes the same condition gave 71/73 with a 165 s run, a
Workspace compile of ~10 s inside the suite, a 31.5 s cache write, and a
create → Workspace wait of 5 s+ on the specs that failed. Then the literal
target, `make test-e2e`, once from the same checkout: 73 passed in 1.3 min,
stack torn down.

Gates on the final code: `make check` 650 passed; `make test-postgres` 760
passed; `pnpm typecheck`, `pnpm lint`, `pnpm format:check` clean;
`pnpm test:unit` 115 passed (12 files, including the new hydration test).

What is still true and worth knowing: the engine's synchronous store calls
in the create and single-campaign read paths still run on the event loop
(stalls of up to 0.7 s under the suite's load — not a failure, a cost); the
onboarding and tenantless projects still share a mutable fixture and skip
the rest of their file when one spec fails (unchanged, by design); and the
dev server's per-request cost is what it is. A production build
(`next build` + `next start`) for the gate would remove the compile-on-demand
class entirely rather than warming its way around it — measured separately,
see the closing comment.

### A better gate: measured, not adopted here (2026-09-10)

Causes 1 and 2 exist only because the gate runs the browser suite against
`next dev`. Warming a route is a list someone must remember to extend — the
Workspace was missed exactly that way — and switching off a cache is a knob.
A production build has neither: every route is compiled before the server
answers its first request, there is no persistent cache to write, and no
hot-reload machinery on the request path.

Measured with the same suite against the same engine, the web service built
with `next build` and served by `next start` (a compose file kept out of the
tree): the whole stack up in 46 s including a 9 s `pnpm build`; three runs
of 60 s, 55 s and 64 s, all 73 passed, against 73-80 s for the dev server
on the fixed branch. No request logging exists in `next start`, so the
per-request comparison is by suite time only.

Not adopted in this fix because it changes the fast loop's contract: today
`web/` is bind-mounted and served live, so a frontend edit is tested with no
rebuild, and the dev stack and the gate run the same code paths. A
production gate needs the source copied into the image (`NEXT_PUBLIC_*`
baked at build time) and a rebuild per edit, or two web images that can
drift. That is a workflow decision for the owner, and it belongs in its own
issue: the gate on a production build, the fast loop on `next dev`, and the
seed and engine shared between them.

Also left as follow-ups, both product-side and not needed for the suite:
the wizard fires its first server action on mount, before Clerk's script has
necessarily renewed a stale token (a restored tab after a minute idle shows
"could not load your audience segments — Try again", and the retry works);
and the engine's create and single-campaign reads still run their store
calls on the event loop (issue 03 moved only the list).

Landed as `773e464` on branch `diag/e2e-flake-04`, merged to main in
`4c9c1d5` (2026-09-10). The interim patch copy at
`.scratch/e2e-suite-flake/04-fix.patch` was deleted once the merge landed. The
follow-ups named above are filed as issues 05, 06 and 07 in this folder.


## Completion

- Completed: 2026-09-10
- Commit: 773e464 (merged to main in 4c9c1d5)

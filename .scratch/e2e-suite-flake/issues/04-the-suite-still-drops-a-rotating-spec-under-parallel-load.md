# 04 — The e2e suite still drops a rotating spec or two under parallel load

Status: needs-triage
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

- [ ] `make test-e2e` passes on an unchanged checkout, ten runs in a row.
- [ ] The fix is isolation or an honest wait, not `workers: 1` and not a blanket
      timeout raise — serialising the suite hides the contention rather than
      resolving it, and 01 rejected that for the same reason.
- [ ] Whatever the cause turns out to be, it is recorded in this file so a fourth
      rediscovery is unnecessary.
- [ ] `make check` and `make test-postgres` pass.
- [ ] Web gates pass — `pnpm typecheck`, `pnpm lint`, `pnpm format:check`,
      `pnpm test:unit`.

## Blocked by

None — can start immediately.

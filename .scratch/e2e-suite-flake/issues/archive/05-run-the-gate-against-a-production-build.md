# 05 — Run the e2e gate against a production build, and keep the dev server for the fast loop

Status: completed
Type: task

## Parent

[04 — The e2e suite still drops a rotating spec or two under parallel load](archive/04-the-suite-still-drops-a-rotating-spec-under-parallel-load.md)

## What to build

Two of the five causes behind issue 04 exist only because `make test-e2e`
drives the browser suite against `next dev`: a route is compiled the first
time it is hit, so any route missing from the setup project's warm list is
paid for inside a spec's assertion, and Turbopack's dev-mode machinery — the
filesystem cache it writes, hot reload on the request path — runs during the
suite. Both were worked around in 04 (a warm list, a switched-off cache).
Working around them leaves a list someone must remember to extend, and the
Workspace was missed exactly that way.

Serve the gate from a production build instead: the `web` service that
`make test-e2e` starts is built with `next build` and served by `next start`,
so every route is compiled before the first request and there is no dev
cache to write. The fast loop keeps what it has today — `make e2e-up` with
`web/` bind-mounted and served by `next dev`, so a frontend edit is tested
with no rebuild — and `make dev` is untouched.

Measured while diagnosing 04, with the same suite and engine: the whole
stack up in 46 s including a 9 s `pnpm build`; three runs of 60 s, 55 s and
64 s, all 73 passed, against 73-80 s for the fixed dev server. The compose
file used for the measurement is a scratch copy of `docker-compose.e2e.yml`
with the web service built from an inline Dockerfile (`COPY . .`, build args
for the `NEXT_PUBLIC_*` values, `pnpm build`, `pnpm start`) and no bind
mounts; it is the starting point, not the design.

Constraints, so the two ways of running the web app cannot drift:

- One compose file. The production web service is a compose profile or an
  override on the same file, sharing `postgres`, `seed` and `engine` with
  the dev one — never a second copy of the stack.
- One Dockerfile. A multi-stage `web/Dockerfile` with a dependencies stage
  the dev service stops at and a build stage the gate uses, rather than two
  files that must be kept in step.
- `NEXT_PUBLIC_*` values are inlined at build time, so they arrive as build
  args read from `web/.env.local` — the same source the runtime environment
  already reads — and `.dockerignore` keeps `.env*` out of the image as it
  does today.
- `make test-e2e` keeps its shape: build, start, seed, run, tear down, under
  `caffeinate` where it exists. `make e2e-up`, `make e2e-test-reset` and the
  fast loop are unchanged. The warm list in `web/tests/auth.setup.ts` stays,
  since the fast loop still needs it; a comment there should say the gate
  does not.
- `CLAUDE.md`'s "Running the e2e suite" section and the table of what to run
  after what kind of change are updated: with the gate on a production
  build, a frontend edit is only verified by `make test-e2e` once the image
  is rebuilt, which `make test-e2e` always does.

## Acceptance criteria

- [x] `make test-e2e` runs the suite against a `next start` server built by
      (The `web-built` service: `web/Dockerfile`'s `production` stage copies
      the source in and runs `pnpm build`; its command is `next start`. Every
      web-container log across fourteen gate runs opens with `✓ Ready in
      ~130ms` and carries no `Compiling` and no `Finished writing to filesystem
      cache` line — counted per run in the table below.)
      `next build` inside the image; the web container's log carries no
      `○ Compiling` line and no `Finished writing to filesystem cache` line.
- [x] `make e2e-up` still serves the working tree live through `next dev`,
      (Stack up with `make e2e-up`, a marker edited into the Pricing page's
      eyebrow, `curl /pricing` returned it on the first poll with no rebuild;
      then `make e2e-test-reset && cd web && E2E_STACK=compose pnpm test`: 73
      passed in 102 s on the dev server; edit reverted.)
      and `make e2e-test-reset && cd web && E2E_STACK=compose pnpm test`
      still passes against it without a rebuild after a frontend edit.
- [x] Both services come from the same compose file and the same
      (`web` and `web-built` in `docker-compose.e2e.yml`, both built from
      `web/Dockerfile` — `target: dependencies` and `target: production` —
      sharing `postgres`, `seed` and `engine`; their common definition is two
      extension fields merged into each. `docker compose config` lists exactly
      five services.)
      Dockerfile; there is no second copy of the postgres, seed or engine
      definitions.
- [x] `make test-e2e` passes ten runs in a row from a clean checkout, and
      (Fourteen runs in a row, table below; the literal `make test-e2e` target
      once more at the end. Wall time per run 73–83 s with the image cached,
      107 s when it builds, against issue 04's 73–80 s for the fixed dev server
      — the suite itself takes 57–68 s here against 60–80 s there.)
      its wall time is recorded here against the 73-80 s of issue 04's
      acceptance runs.
- [x] `CLAUDE.md`'s e2e section says which stack each command runs and what
      ("Running the e2e suite" names `web-built` for the gate and `web` for the
      fast loop, the one Dockerfile and its two stages, and the table's first
      row says a frontend edit is fine on either since the gate rebuilds.)
      a frontend edit needs before each is trustworthy.
- [x] `make check` and `make test-postgres` pass. (655 passed / 766 passed.)

## Blocked by

None — can start immediately.

## Comments

### Done (2026-09-10)

Landed as `e56043e`, with review fixes in `511877c` and a spec fix in
`0a4d668`, on branch `e2e-flake-followups`.

### Acceptance evidence (2026-09-10)

Every run is the gate's own shape — `up --build --wait engine web-built`,
the suite, the web log captured, `down -v` — driven by a script from a
worktree of the branch, under `caffeinate`. Runs 1–5 were on `e56043e`, runs
6–10 on the review fixes `511877c` (run 6 paid the rebuild), runs 11–13 on the
spec fix `0a4d668`. "Compile lines" counts `Compiling` and `Finished writing
to filesystem cache` in the web container's log.

| Run | Result | Stack up | Suite | Total | Compile lines |
| --- | --- | --- | --- | --- | --- |
| 1 | 73 passed | 43 s (image built) | 64 s | 107 s | 0 |
| 2 | 73 passed | 18 s | 60 s | 78 s | 0 |
| 3 | 73 passed | 17 s | 59 s | 76 s | 0 |
| 4 | 73 passed | 15 s | 63 s | 78 s | 0 |
| 5 | 73 passed | 16 s | 67 s | 83 s | 0 |
| 6 | 73 passed | 49 s (image rebuilt) | 68 s | 117 s | 0 |
| 7 | 73 passed | 15 s | 64 s | 79 s | 0 |
| 8 | 73 passed | 16 s | 58 s | 74 s | 0 |
| 9 | 73 passed | 16 s | 59 s | 75 s | 0 |
| 10 | 73 passed | 16 s | 57 s | 73 s | 0 |
| 11 | 73 passed | 28 s (image rebuilt) | 68 s | 96 s | 0 |
| 12 | 73 passed | 16 s | 60 s | 76 s | 0 |
| 13 | 73 passed | 13 s | 65 s | 78 s | 0 |

Between runs 10 and 11 the literal `make test-e2e` target, run once on
`511877c`, dropped **one** spec: `home.spec.ts:75`, "a decision made in the
Workspace is reflected on Home without a refresh", at its last assertion.
Playwright's snapshot showed the campaign on Home as "In progress 3/6 stages"
rather than on the decision queue: the spec had approved Brand strategy, seen
it marked Approved, and opened Home at once — but "Approved" shows the moment
the run resumes, while Campaign strategy is still being produced, so Home
read in that window honestly says "in progress". The spec assumed the run had
already halted at the next gate; the production build renders Home faster
than the dev server did, which widened the window. Fixed in `0a4d668` by
waiting for the Approve button to return before opening Home, the same wait
the spec already used after Start run. Runs 11–13 and one more literal
`make test-e2e` (73 passed, 84 s, no containers left) followed.

**Decisions taken here, not in the issue.**

- A second service sharing anchors rather than a compose profile. With a
  profile, `down`, `logs` and `ps` would each need the profile named to see
  the gate's container; as two plain services, everything works with no flag,
  and the Makefile naming one or the other is what keeps them apart (both bind
  3100). The compose file says so.
- `docker-compose.yml` (the `make dev` stack) gained `target: dependencies`.
  The issue said `make dev` is untouched, and its behaviour is — but with a
  multi-stage Dockerfile the *last* stage is the default, so without the line
  `make dev` would have built and served a production image.
- `web/.dockerignore` now excludes `.env*` rather than `.env.local` and
  `.env` by name: with `COPY . .` in the production stage, a stray
  `.env.production` would otherwise have been copied into the image.

**Worth knowing.** The web container logs `Clerk: Refreshing the session token
resulted in an infinite redirect loop` three times per suite run — on the dev
server too (three in the fast-loop run above), so it predates this change.
Not diagnosed here; most likely the tenantless specs' sign-in/sign-out churn.

## Completion

- Completed: 2026-09-10
- Commit: e56043e, with review fixes in 511877c and the Home spec wait in 0a4d668 on branch `e2e-flake-followups` (merged to main in 9a4fc6f)

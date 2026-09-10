# 05 — Run the e2e gate against a production build, and keep the dev server for the fast loop

Status: ready-for-agent
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

- [ ] `make test-e2e` runs the suite against a `next start` server built by
      `next build` inside the image; the web container's log carries no
      `○ Compiling` line and no `Finished writing to filesystem cache` line.
- [ ] `make e2e-up` still serves the working tree live through `next dev`,
      and `make e2e-test-reset && cd web && E2E_STACK=compose pnpm test`
      still passes against it without a rebuild after a frontend edit.
- [ ] Both services come from the same compose file and the same
      Dockerfile; there is no second copy of the postgres, seed or engine
      definitions.
- [ ] `make test-e2e` passes ten runs in a row from a clean checkout, and
      its wall time is recorded here against the 73-80 s of issue 04's
      acceptance runs.
- [ ] `CLAUDE.md`'s e2e section says which stack each command runs and what
      a frontend edit needs before each is trustworthy.
- [ ] `make check` and `make test-postgres` pass.

## Blocked by

None — can start immediately.

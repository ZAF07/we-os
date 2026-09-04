# 14 — The e2e stack leaves an orphaned image behind on every run, until the disk fills and the suite times out

Status: ready-for-agent
Type: bug

## Parent

[PRD: we-OS SaaS foundation](../PRD.md) · follows [13 — the e2e stack](archive/13-frontend-suite-cannot-run-without-credentials.md)

## Symptom

`make test-e2e` tears down its **containers, networks and volumes** correctly —
`docker compose down -v` runs whether the suite passes or fails, and afterwards
there are zero `we-os-e2e` containers and zero `we-os-e2e` volumes.

What it does **not** clean up is the **image** each `--build` replaces. Every run
rebuilds, the previous image is orphaned as a dangling layer set, and nothing
ever reclaims it. The web image is 1.14 GB, so the disk grows by roughly that
much per run.

Measured on 2026-09-04, after a session of repeated runs:

```
=== dangling images ===
7fa9aad29d71    1.14GB    11 minutes ago
2482bd00de79    1.14GB    15 minutes ago
c7fa1d7cfcaf    1.14GB    20 minutes ago
28cfe1a19fbf    1.14GB    23 minutes ago
9021226af02f    1.14GB    30 minutes ago
```

Five orphans — 5.7 GB — from half an hour of work. Build cache grew alongside
them to **20.51 GB**, with images at 15.18 GB (89% reclaimable).

**The impact is not just disk.** As Docker Desktop's allocation fills, the web
container is starved and the Next dev server compiles routes slowly. Specs then
fail on a slow first paint, which looks exactly like a product defect:

- A clean run: **36 passed in ~35s**.
- The same code once the disk had filled: **20 failed, 16 passed, 3.3 minutes**,
  with specs hitting the full 2-minute timeout.

That second result cost real time to diagnose, because the failures pointed at
the Workspace rather than at the environment. A suite whose reliability decays
with the number of times it has been run is worse than a slow one — it teaches
you to distrust real failures.

## Repro

Deterministic.

```bash
docker system df                 # note "Images" and "Build Cache"
make test-e2e
docker images -f "dangling=true" # one new 1.14GB orphan per run
docker system df                 # both totals have grown
```

Repeat a few times and the growth is linear. Nothing in the Makefile or the
compose file ever removes an image or prunes cache.

## What's wanted

The stack should leave **nothing** behind — that is the whole premise of a
throwaway test environment, and it is already true of containers and volumes.
Images and build cache are the gap.

Worth deciding as part of the fix:

- Whether teardown prunes only what this stack created (safest — the machine
  runs other projects' containers, which a blanket `docker system prune` would
  disturb) or offers a separate opt-in deep clean.
- Whether the rebuild is even needed every run. `--build` on every invocation is
  what orphans an image; building only when inputs changed would mostly remove
  the problem rather than clean up after it.
- Whether the web image needs to be 1.14 GB. It carries a full `node_modules`
  for a container that bind-mounts the working tree anyway (see 13), so there
  may be much less to build in the first place.

## Acceptance criteria

- [ ] Running `make test-e2e` repeatedly does not grow Docker's image total without bound, including when source changes between runs.
- [ ] Build-cache growth is reduced to the point of not mattering, and a documented command reclaims what remains. It cannot be driven to zero: the engine legitimately copies its source, so a Python change adds a cache entry, and BuildKit stamps no project label on cache so it cannot be pruned automatically without touching other projects.
- [ ] Teardown removes what this stack created and leaves other projects' containers, images and volumes untouched.
- [ ] `docker system df` before and after a run shows no net growth, demonstrated in the issue's closing note.
- [ ] The suite's runtime does not degrade across consecutive runs — three back-to-back runs stay within a comparable duration.
- [ ] `make test-e2e` still passes: 36 passed, 0 failed, 3 skipped.
- [ ] The engine gates still pass — `uv run ruff check .`, `uv run mypy src`, `uv run pytest`.

## Suspected location

- [`Makefile`](../../../Makefile) — `test-e2e` runs `$(COMPOSE) down -v`, which handles containers, networks and volumes but never images or cache. `--build` on every `up` is what creates the orphan.
- [`web/Dockerfile`](../../../web/Dockerfile) — the 1.14 GB image; it installs the full dependency tree into an image whose source is bind-mounted at runtime.

## Comments

**2026-09-04.** Filed after it bit during issue 11's verification. Reclaiming
the space by hand (`docker builder prune -af`, `docker image prune -af`)
recovered **43 GB** and restored the suite to ~35s, which is how the cause was
confirmed. Note that reclaiming alone did not fix the failures in that session —
the parallel-worker saturation addressed in `37f4321` was a second, independent
cause. Both produced the same symptom, which is part of why this is worth
removing as a variable.

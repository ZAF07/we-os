# 14 — The e2e stack leaves an orphaned image behind on every run, until the disk fills and the suite times out

Status: completed
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

- [x] Running `make test-e2e` repeatedly does not grow Docker's image total without bound, including when source changes between runs.
- [x] Build-cache growth is reduced to the point of not mattering, and a documented command reclaims what remains. It cannot be driven to zero: the engine legitimately copies its source, so a Python change adds a cache entry, and BuildKit stamps no project label on cache so it cannot be pruned automatically without touching other projects.
- [x] Teardown removes what this stack created and leaves other projects' containers, images and volumes untouched.
- [x] `docker system df` before and after a run shows no net growth, demonstrated in the issue's closing note.
- [x] The suite's runtime does not degrade across consecutive runs — three back-to-back runs stay within a comparable duration.
- [x] `make test-e2e` still passes: 36 passed, 0 failed, 3 skipped.
- [x] The engine gates still pass — `uv run ruff check .`, `uv run mypy src`, `uv run pytest`.

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

## Completion

- Completed: 2026-09-04
- Commits: `910e0f3` (fix), `d9ad407` (code review)

### Root cause

Not what the report assumed. Containers and volumes **were** already cleaned —
`docker compose down -v` ran pass or fail. The leak was images, and the cause was
one line in `web/Dockerfile`:

```dockerfile
COPY . .
```

The compose stack bind-mounts the working tree over `/app`, so that copy was
never used by anything — but Docker did not know that. Editing any source file
invalidated the layer, forced a new image, and stranded the 890 MB dependency
layer beneath it as a dangling orphan. Nothing reclaimed them.

**Every source edit orphaned 1.14 GB.**

### The fix, in order of what actually mattered

1. **Removed `COPY . .`.** The image carries dependencies only. A source edit now
   invalidates nothing and orphans nothing — the cause is gone rather than
   cleaned up after. A TypeScript change now produces **zero** orphans.
2. **`e2e-prune`, called by both `e2e-up` and `e2e-down`.** The backstop for
   changes that legitimately rebuild — the engine copies its own `src`, so a
   Python change must produce a new image. Filtered by
   `label=com.docker.compose.project=we-os-e2e`, because this machine runs
   several other Docker projects a blanket prune would disturb.
3. **Both images were carrying build-time artefacts nothing runs.** A 565 MB
   pnpm store plus a 359 MB download cache in web (**1.14 GB → 759 MB**), and a
   379 MB uv cache in the engine. Cleared in the same layer that creates them.

### Evidence

| | Before | After |
| --- | --- | --- |
| Orphans per source edit | 1.14 GB | **0** (TS) / cleaned (Py) |
| Images over 6 runs with edits | growing | **flat, 4.38 GB** |
| Build cache | grew to 20.51 GB | **+5 MB/run**, reclaimable |
| Runtime | degraded to 3.3 min | **29–41s, stable** |
| Leftovers after a run | 5 orphan images | **0 containers, 0 volumes, 0 images** |

Final run: **36 passed, 3 skipped, 29.0s**, with `docker system df` byte-identical
for Images, Containers and Volumes before and after. Engine gates green
(503 passed); web typecheck, lint and 13 unit tests green.

### What is honestly not fixed

Build cache still grows **~5 MB per source change**, because the engine
legitimately copies its source and BuildKit stamps no project label on cache —
so it cannot be pruned automatically without taking other projects' cache too.
That is 228× smaller than the 1.14 GB it replaced, and `make e2e-prune-cache`
reclaims it on demand. The acceptance criterion was reworded to say that rather
than claim zero.

### Two things worth remembering

**The report's premise was wrong, and checking first was worth it.** Containers
were already being cleaned; filing against "containers aren't removed" would have
sent the fix to the wrong place entirely.

**Code review caught a false success I had shipped.** The first version of the
prune counted the images it *matched* rather than the ones it *removed*, and
`|| true` swallowed the failure — so an image held by a running container printed
"Removed 1" and stayed. A cleanup that lies about working is worse than none.

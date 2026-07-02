# Harden PlaywrightWebSearch close/concurrency edge cases

Status: ready-for-agent

## Parent

`.scratch/fix-playwright-enabled-issue/issues/01-fix-playwright-greenlet-thread-affinity.md`

## What to build

Code review of the thread-confinement fix found the backend is safe for the
runner's sequential lifecycle but not yet for fully arbitrary callers:

1. `close()` racing an in-flight `search()`/`fetch()`: the worker executor is
   captured under the lock but submitted to after releasing it, so a
   concurrent `close()` can trigger `RuntimeError: cannot schedule new futures
   after shutdown` — or, in a worse interleaving, relaunch Chromium on the
   dying worker and leave a stale browser that reintroduces the original
   greenlet error on the next call.
2. If browser teardown raises on the worker thread, the Playwright driver is
   never stopped and the stale browser handle survives into the next worker,
   again reintroducing the cross-thread greenlet error.
3. The regression suite never exercises `close()` with a live browser, so the
   teardown half of the original bug has no direct test; reuse-after-close
   (which silently resurrects a fresh executor and browser) is likewise
   untested and undocumented.

Make dispatch-vs-close atomic (submit under the lock or equivalent), make
teardown exception-safe so driver stop and handle clearing always happen, and
lock the close path and reuse-after-close behaviour down with offline tests.

## Acceptance criteria

- [ ] A `close()` concurrent with in-flight `search()`/`fetch()` calls neither raises `RuntimeError` from executor shutdown nor leaves a browser handle a later call would touch cross-thread.
- [ ] An exception during browser teardown still stops the Playwright driver and clears both handles.
- [ ] Tests cover the worker-thread `close()` path and reuse-after-close, offline via the existing fake seam; `close()` docstring states the reuse behaviour.
- [ ] `ruff check`, `ruff format`, `mypy src`, and `pytest` all pass.

## Blocked by

- `.scratch/fix-playwright-enabled-issue/issues/01-fix-playwright-greenlet-thread-affinity.md`

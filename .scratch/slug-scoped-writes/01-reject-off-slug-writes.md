# Reject off-slug writes

Status: ready-for-agent

Source: `docs/adr/0006-recoverable-tool-errors-and-slug-anchored-seeds.md` — "Known limitation (deliberately deferred)".

## What to build

Close the deferred limitation in ADR-0006: a mis-slugged `write_file` currently succeeds silently. The sandbox permits any path under `campaigns/**`, and the specialist's tools are built once at graph-build time — before any run's slug is known — so nothing rejects a write to the wrong campaign. When the model hallucinates the slug (e.g. `coast-coffee-test-two` → `coast-coast-test-two`), the deliverable lands at the wrong path, and the review node then reads the correct-but-stale file at `campaigns/<slug>/<deliverable>.md`.

Make the write tool aware of the **live run slug** at invocation time and reject any write whose path is not under `campaigns/<slug>/`, raising a `ToolError`. The existing `recover_tool_errors` middleware (`agents/middleware.py`) already converts a raised `ToolError` into a recoverable error tool-result, so the specialist sees the failure and self-corrects with the right slug — no new error-handling path is needed. Once it writes to the correct path, the review node reads the fresh deliverable.

**Recommended mechanism (per-run tool binding via `InjectedState`):** the run slug already lives on `CampaignState["slug"]`. Give `write_file` an `InjectedState`-annotated parameter (hidden from the model) so it reads the live slug at call time and validates the path against `campaigns/<slug>/`. This works with the prebuilt `ToolNode` that `create_agent` uses and needs no runner changes. The path check itself belongs in the sandbox (a slug-scoped write) rather than the tool wrapper, so it stays covered by sandbox-level tests. Confirm `InjectedState` composes with the `recover_tool_errors` `wrap_tool_call` middleware before committing to it; if it does not, fall back to threading the slug through `config['configurable']`.

Keep the guard specific: the raised `ToolError` message should name both the slug the model used and the run slug, and instruct it to use the run slug verbatim — mirroring the tone of `_path_anchor` in `graph/nodes.py` — so the recoverable retry has what it needs to correct.

## Acceptance criteria

- [ ] A `write_file` call whose path is not under `campaigns/<run-slug>/` is rejected with a `ToolError` (not written to disk) rather than succeeding silently.
- [ ] The rejection is recoverable: the specialist receives an error tool-result via `recover_tool_errors` and can retry, and a subsequent correctly-slugged write succeeds and is picked up by the review node.
- [ ] The error message names the offending slug and the correct run slug and tells the model to use the run slug verbatim.
- [ ] A correctly-slugged write under `campaigns/<run-slug>/` still succeeds unchanged (existing happy-path, save-retry, and QA-loop tests keep passing).
- [ ] Writes outside `campaigns/**` remain rejected as before (existing write-prefix guard is not weakened).
- [ ] New tests cover: off-slug write rejected + recovered, and correct-slug write unaffected. Add a graph-level test alongside `test_bad_path_tool_error_is_recoverable_not_fatal` and a sandbox-level unit test for the slug-scoped write.
- [ ] The "Known limitation (deliberately deferred)" note in `docs/adr/0006-...md` is updated to record that off-slug writes are now guarded (with the mechanism used), rather than left as a follow-up.
- [ ] `uv run ruff check .`, `uv run ruff format`, `uv run mypy src`, and `uv run pytest` all pass, and the result is reported explicitly.

## Blocked by

- None - can start immediately.

# 0006 — Recoverable tool errors and slug-anchored specialist seeds

Specialist tool errors are returned to the model as an error tool-result, never raised out of the tool node, and every specialist seed message restates the campaign slug and its path prefix. Both changes exist because specialists must hand-type file paths (e.g. `campaigns/<slug>/campaign-strategy.md`) in their tool calls, and a single mis-typed character was fatal.

## Context

`ToolError` was always *documented* as recoverable (see [ADR-0005](0005-code-enforced-filesystem-sandbox.md) and the docstrings in `adapters/tools/filesystem.py` and `errors.py`), but the behaviour was never wired up. `create_agent` builds a `ToolNode` whose default `handle_tool_errors` (`_default_handle_tool_errors`) only rescues LangGraph's own `ToolInvocationError` (argument-schema validation) and **re-raises everything else** — including `marketing_os.errors.ToolError`. So a routine bad-path tool call propagated out of the tool node and crashed the whole graph run.

This bit in production: on the second `campaign-strategy` run (after a QA redo), the model hallucinated the slug `coast-coffee-test-two` → `coast-coast-test-two` in a `read_file` call and the run died with `ToolError: File not found`. The revision seed made the slip likely — it reset the conversation and mentioned the slug only once, inside a single deliverable path.

## Decision

1. **Recover tool errors in middleware.** A `wrap_tool_call` middleware (`agents/middleware.py::recover_tool_errors`) catches `ToolError` and returns a `ToolMessage(status="error")`, so the specialist sees the failure and self-corrects. Wired into every specialist via `create_agent(..., middleware=[recover_tool_errors])`. This is the only extension point `create_agent` exposes for tool-error handling.
2. **Remove the failing operation from the redo loop.** The review node already reads the prior draft, so the revision seed now **inlines that draft** instead of instructing a `read_file` — the redo loop no longer reads a hand-typed path at all.
3. **Anchor the slug in every seed.** `_path_anchor(slug)` prepends a prominent "the slug is `<slug>`; use it verbatim" block to the enter, revise, and save-retry seeds, giving the remaining hand-typed path (the `write_file` save) a redundant, hard-to-corrupt reference.

## Consequences

- An LLM path slip is now survivable: the model retries against the error message rather than crashing the run. ADR-0005's "recoverable, not a crash" claim is finally true in code.
- The redo loop cannot fail on a mis-typed *read* path — there is no read to mistype.
- **Off-slug writes are now guarded (follow-up closed).** A mis-slugged `write_file` previously succeeded silently, because the sandbox allowed any path under `campaigns/**` and the tools are built once at graph-build time, not bound to the run's slug — the review node then read the correct-but-stale deliverable. `write_file` now takes an `InjectedState("slug")` parameter (hidden from the model) so it reads the live run slug at call time, and `FilesystemSandbox.write` scopes the write to `campaigns/<slug>/`, raising a `ToolError` (naming both the offending slug and the run slug, and instructing verbatim use) when the path is off-slug. The error flows through `recover_tool_errors` as a recoverable tool-result, so the specialist self-corrects and the review node reads the fresh deliverable. Slug anchoring and the save-retry remain as complementary mitigations.

## Evidence

- `agent-harness/src/marketing_os/agents/middleware.py` (`recover_tool_errors`); wired in `agents/specialist.py::build_specialist`.
- `agent-harness/src/marketing_os/graph/nodes.py` (`_path_anchor`, inlined-draft `revise_body`, anchored enter/save-retry seeds).
- `agent-harness/tests/test_graph.py` (`test_bad_path_tool_error_is_recoverable_not_fatal`, `test_off_slug_write_rejected_then_recovered`, `test_revision_inlines_draft_and_requires_no_read`, `test_seeds_anchor_the_campaign_slug`); `agent-harness/tests/test_sandbox.py` (slug-scoped write).
- Off-slug guard: `agent-harness/src/marketing_os/adapters/tools/filesystem.py` (`write_file`'s `InjectedState("slug")`), `adapters/tools/sandbox.py` (`FilesystemSandbox.write` slug scope), `agents/specialist.py` (`SpecialistState`), `graph/nodes.py` (specialist node threads `slug` into the agent state).
- Root cause: `langgraph/prebuilt/tool_node.py::_default_handle_tool_errors`; `langchain/agents/factory.py` builds its `ToolNode` without overriding `handle_tool_errors`.

# 0005 — Code-enforced filesystem sandbox

Agent file access is scoped in code, not by prompt instruction: agents may read anywhere under the repo root but may write only under `campaigns/**`. We enforce this in `FilesystemSandbox` (`adapters/tools/sandbox.py`) rather than trusting the model to obey a "don't write elsewhere" instruction, because prompt-based restrictions are not a security boundary.

The sandbox resolves paths and rejects escapes with `is_relative_to`, caps reads at ~400KB per file and grep at 200 matches, and raises `ToolError` (a recoverable tool error) on violation. The same scope is mirrored in `.claude/settings.json` for the interactive path, which pre-allows only `Write(campaigns/**)` and `Edit(campaigns/**)` plus read-only tools.

## Consequences

- Deliverables can only land in `campaigns/**`; `knowledge/` stays read-only (the write-back capability is deliberately inactive — see `knowledge/README.md`).
- A stage that tries to write outside scope fails as a tool error the agent can recover from, not a crash.

## Evidence

- `agent-harness/src/marketing_os/adapters/tools/sandbox.py` (`FilesystemSandbox`, `is_relative_to`, read/grep caps).
- `.claude/settings.json` (`Write(campaigns/**)`, `Edit(campaigns/**)` only).

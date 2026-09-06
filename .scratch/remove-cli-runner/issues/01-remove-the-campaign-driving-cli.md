# 01 — Remove the campaign-driving CLI and the runner paths that served it

Status: ready-for-agent
Type: task

## Parent

[ADR-0026: The API is the only campaign execution surface](../../../docs/adr/0026-the-api-is-the-only-campaign-execution-surface.md) · follows [ADR-0012](../../../docs/adr/0012-nextjs-frontend-and-bff-in-monolith.md)

## Why

The CLI's campaign commands existed to exercise the pipeline before there was a
frontend. The FE/BE integration is done and local work now happens through
`make dev`, so that surface is redundant — and it was never equivalent to the
API. It ran campaigns uncharged and unversioned, and gated a filesystem Brand DNA
against a database-published question set.

This is one subtraction, not a refactor. Nothing on the API path changes
behaviour.

## Scope

**Deleted — the campaign-driving interface** (`agent-harness/src/marketing_os/entrypoints/cli.py`):

- `_cmd_new_campaign`, `_cmd_check`, `_cmd_agents` and their subparsers
- `_render_event`, `_print_gate`, `resolve_questionnaire`,
  `read_published_questionnaire`, `_resolve_tenant` — all orphaned by the above
- The module-level imports that only these used: `FilesystemDocumentStore`,
  `check_gate`, `GateReport`, `SEED_QUESTIONNAIRE`, `Settings`/`load_settings`,
  and the `GateError`/`GuardrailError` handling in `main` if nothing else raises them

**Deleted — runner paths with no remaining production caller:**

- `graph/runner.py` `run_campaign` — the sync wrapper, whose docstring says it
  exists "for the CLI". Takes no `deliverable_store` and no `usage_ledger`.
- `graph/runner.py` `astream_campaign` — same omission, one test caller
- `graph/state.py` `revisions` (no writer, no reader) and `governance`
  (written at `nodes.py:380`, never read), plus the module docstring paragraph
  at `state.py:8` describing `revisions`

**Kept — admin plumbing, unchanged:**

- `_cmd_init_db`, `_cmd_publish_questionnaire`, `load_questionnaire_file`,
  `build_parser`, `main`. Both commands take an explicit `--dsn`, use lazy local
  imports, and touch no campaign machinery.
- The `marketing-os` console script, `pyproject.toml`, and both compose files'
  `migrate` services stay as they are.

## Tests

Anything that exists because of a deleted item is deleted with it. Anything that
used a deleted item incidentally is rewritten with its assertions intact.

- `tests/test_cli.py` — delete the ~15 tests of `check`, `agents` and
  `new-campaign`. Keep `test_publish_questionnaire_is_registered_with_its_dsn_and_file`
  and the three `load_questionnaire_file` tests. Check whether
  `test_config_error_when_root_missing_claude_dir` still has a subject.
- `tests/test_runner_checkpoint.py` (3 sites) — tests checkpointing, not the CLI.
  Rewrite to `asyncio.run(arun_campaign(...))`, same assertions.
- `tests/test_observability.py` (6 sites) — five rewrite the same way. Delete
  `test_crashed_astream_writes_terminal_error_event`: it duplicates
  `run.summary outcome=error` on the streaming path, and its non-streaming
  sibling (line ~125) already asserts it.
- `tests/test_tenancy.py:365,379` — imports `main` and `build_parser`; confirm
  what it drives and keep it only if it exercises a surviving command.
- `tests/test_postgres.py:499` — uses `load_questionnaire_file`, which survives.

## Follow-on, in the same change

With no CLI caller left, `governance/gate.py` `check_gate` can take
`questionnaire` as a **required** parameter. All three remaining callers (all in
`app.py`) pass the published set; only `graph/nodes.py:369` omits it and silently
falls back to the hand-authoring template, so the graph's own gate enforces a
weaker rule than every entrypoint.

Not currently reachable — `gate` is wired at `START` and a resume continues from
the interrupted node, so every path that executes it was already gated by the
API. Fix it anyway: it reads as a safety net and is not one.

## Docs

- `README.md:70-72,173` — remove the `new-campaign` / `check` / `agents` examples.
- `src/marketing_os/__init__.py:10` — the module docstring names `run_campaign`.
- `agent-harness/Makefile` — no change; `db-up` uses `init-db`, which survives.

## Acceptance criteria

- [ ] `marketing-os --help` lists exactly `init-db` and `publish-questionnaire`.
- [ ] `run_campaign`, `astream_campaign`, `state.revisions` and `state.governance` are gone, and nothing imports them.
- [ ] `check_gate` requires `questionnaire`; `graph/nodes.py:369` passes the published set.
- [ ] No test asserts on a deleted surface; checkpoint and observability coverage is unchanged in what it asserts.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` all pass.
- [ ] `make dev` brings the stack up and the schema is provisioned — the `migrate` service still runs `init-db`.
- [ ] `make test-e2e` passes.
- [ ] A campaign runs end to end through the UI at http://localhost:3000.
- [ ] README carries no CLI campaign examples.

## Verification

`make dev` is the one that matters: `init-db` lives in the file being edited, and
both compose stacks depend on it. Green tests do not prove the stack still comes
up.

## Comments

**2026-09-06.** Scoped in a `/grill-with-docs` session on the architecture review
of the same date. Decisions recorded in
[ADR-0026](../../../docs/adr/0026-the-api-is-the-only-campaign-execution-surface.md).

Traced during that session and worth not re-deriving: the review called the gate
divergence "arguably a live defect"; it is not reachable today, because `gate` is
the `START` node and `Command(resume=...)` continues from the interrupted node
rather than re-entering `START`. All four graph entry paths are gated by an
entrypoint first. It is latent, and the required parameter is what keeps it that way.

This closes review candidates **05** (gate divergence — the CLI half disappears
with the surface) and **09** (dead state fields and the duplicated stream path).
Candidates **01, 02, 03, 04, 10** are untouched and still open; **02** (one
composition root) gets smaller once there is one entrypoint left to build
dependencies for.

# Crashed runs leave no terminal trace event; stage logs carry no slug

Status: ready-for-agent

## Symptom

After the `coast-coffee-test-four` run 500'd (see
`.scratch/web-tool-hardening/issues/01-recover-web-tool-navigation-errors.md`),
the server console kept emitting `stage.review` / `stage.done` / `stage.start`
lines, which read as "the crashed pipeline is still running behind the scenes".

## Diagnosis (confirmed from run traces on disk)

It was **not** a zombie of the crashed run. Two runs overlapped:

- `logs/coast-coffee-test-three/20260702T144659Z-52ea593b.jsonl` — started
  14:46:59Z, still progressing at 14:58Z (research passed, brand-strategy took
  3 QA retries, then campaign-strategy started).
- `logs/coast-coffee-test-four/20260702T144811Z-56860d52.jsonl` — started
  14:48:11Z, died in the research stage; **the trace just stops** at
  `stage.start research` (3 events).

The post-500 console lines all belonged to the test-three run. Two
observability defects made this indistinguishable from a zombie run:

1. **No terminal event on crash.** In `run_campaign`
   (`agent-harness/src/marketing_os/graph/runner.py:286-302`),
   `_write_summary` sits on the success path inside the `try`; an unexpected
   exception (anything outside the `MarketingOSError` hierarchy, like the raw
   Playwright error) exits via `finally` without ever writing
   `run.summary outcome=error` to the trace or the console log. A dead run and
   a live run look identical in the logs. `astream_campaign` should be checked
   for the same gap.
2. **Stage log lines carry no run identity.** `gate.*` and `run.start` include
   `customer=`/`slug=`, but `stage.start` / `stage.review` / `stage.done`
   lines (emitted from the graph nodes) do not, so interleaved concurrent runs
   on one console cannot be told apart.

## What to build

- Wrap the graph-stream loop so any escaping exception writes a terminal
  `run.summary outcome=error error=<repr>` event to the JSONL trace and the
  console log before re-raising (in both `run_campaign` and
  `astream_campaign`).
- Include the slug (and stage-scoped thread id where relevant) in every
  `stage.*` console log line emitted by the graph nodes.

## Acceptance criteria

- [ ] A run killed by an unexpected exception ends its JSONL trace with a `run.summary` event with `outcome=error` and the error message; the console shows the matching `run.summary` line.
- [ ] Every `stage.*` console log line includes the campaign slug.
- [ ] Tests cover the crash path (fake node raising a non-`MarketingOSError`) and assert the terminal trace event.
- [ ] `uv run ruff check .`, `uv run ruff format`, `uv run mypy src`, `uv run pytest` all pass.

# The API is the only campaign execution surface

A campaign runs one way: `POST /campaigns/{slug}/runs` on the FastAPI engine, driven by the Next.js frontend. The CLI's campaign-driving commands — `new-campaign`, `check`, `agents` — are removed, along with the sync `run_campaign` and `astream_campaign` wrappers that existed to serve them.

The CLI run path was scaffolding. It existed to exercise the pipeline before there was a frontend to do it, and ADR-0012's FE/BFF integration retired that need. Keeping it meant maintaining a second way to execute a campaign that had already drifted from the first.

`marketing-os` survives as an **admin** CLI with two commands that have no API equivalent and never drove a campaign: `init-db` (provisions the schema and grants the app role — needs administrative rights the service deliberately lacks, per ADR-0023) and `publish-questionnaire` (the "editable without a deploy" path from ADR-0018). Both are invoked by `make dev` and `make test-e2e` through the compose `migrate` service.

## Why the run path went rather than being fixed

The second execution surface was not merely redundant — it enforced weaker rules than the API:

- **Uncharged and unversioned.** `run_campaign` and `astream_campaign` take no `deliverable_store` and no `usage_ledger`, so both fall back to filesystem defaults (`graph.py:209-215`). A CLI run wrote deliverables nowhere the API could see and consumed no quota, which ADR-0020 makes load-bearing.
- **A split-brain gate.** `cli.py` hardcoded `FilesystemDocumentStore` while `resolve_questionnaire` read the published set from Postgres when a DSN was set — gating a filesystem Brand DNA against a database question set. `resolve_questionnaire`'s own docstring named this hazard ("would let the CLI pass a business the API blocks"); the document store slipped through the same gap.

Fixing both would have meant giving the CLI the API's full dependency construction — a second composition root to keep in step by hand, which is how the drift arose. Deleting the surface removes the class of defect instead of the instances.

## Considered options

- **Delete the campaign-driving commands, keep the admin ones (chosen)** — removes the divergence structurally; `make dev` and `make test-e2e` keep working unchanged.
- **Delete the CLI entirely** — rejected: `init-db` is the only thing that creates the schema and is called by both compose stacks; `publish-questionnaire` has no API equivalent. Neither is a "test the pipeline without a frontend" tool.
- **Make the CLI mirror the API through one shared execution function** — rejected: correct if a headless surface were needed, but it is not, and it keeps a second entrypoint alive for no current caller.
- **Fix the CLI's stores and leave it** — rejected: preserves two composition roots and the drift they invite.

## Consequences

- **There is no headless way to run a campaign.** Anything scripting the pipeline goes through the HTTP API. If a genuine headless need appears — a scheduled run, a batch backfill — the honest answer is an API client or a worker, not a revived CLI, because those inherit quota and versioning rather than bypassing them.
- `graph/state.py` loses `revisions` and `governance`, both dead. Human revision counts are derived from the deliverable store (`human_revisions_used`), which is where they were already read from.
- Test coverage is unchanged. Checkpoint and observability tests that used `run_campaign` incidentally move to `asyncio.run(arun_campaign(...))` with the same assertions; only tests of the deleted surface itself are removed. The one `astream_campaign` test duplicated an assertion its non-streaming sibling already makes.
- The gate's `questionnaire` parameter can become required (`governance/gate.py`), since only API callers remain and all three pass the published set. That closes a divergence where the graph's own gate node fell back to the hand-authoring template.

## Relationship to other decisions

Follows ADR-0012 (the frontend that made the CLI run path redundant). Preserves ADR-0018's publish path and ADR-0023's split between administrative and application database roles. Does not alter ADR-0015 — approval gates were an API operation already, which is why the CLI could only report a halt rather than answer one.

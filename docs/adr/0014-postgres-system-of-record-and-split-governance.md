# Postgres as the system of record, behind a DocumentStore port, with split governance

Tenant data (Brand DNA, campaign goals, deliverables, run traces) and LangGraph checkpoints move from the repository filesystem into Postgres. Agents keep reading and writing **markdown** — a `DocumentStore` port resolves documents per tenant, with a Postgres adapter in production and a filesystem adapter for local development. Markdown stays the agent I/O format because it preserves the Stage 0 gate's template parsing, the guardrail rubrics, and every specialist prompt unchanged; only the resolution of *where a document lives* moves.

Governance is deliberately **split** rather than moved wholesale:

- **To Postgres** (admin-editable, versioned, no deploy): the onboarding questionnaire, the guardrail rubrics, and the knowledge library — marketing content that will be tuned constantly.
- **Stays code-shipped markdown** (git-versioned, code-reviewed): the eight non-negotiable rules in `.claude/rules/`, the pipeline stage definitions, and the five specialist system prompts — the safety and governance core. An unreviewed edit to an agent's system prompt is how a professional platform silently goes off the rails.

## Considered options

- **Agents emit structured JSON per stage instead of markdown** — rejected: better frontend ergonomics, but it rewrites every specialist prompt, every rubric, and the reviewer, for a benefit the FE can get by rendering markdown.
- **Tenant-scoped filesystem (or object-store prefix) with Postgres only for identity** — rejected: inherits filesystem semantics for everything, with no transactions, no queryable deliverables, and awkward versioning for the revision loop.
- **Move all governance to Postgres and retire `.claude/`** — rejected: puts agent behaviour into unreviewed runtime data and requires building admin editing UI for all of it before there are customers.

## Consequences

- Amends [ADR-0003](0003-governance-as-markdown.md): both layers no longer read the same markdown for every artifact. The `.claude/` interactive layer remains a development and authoring tool against the filesystem adapter, not a product runtime.
- Amends [ADR-0005](0005-code-enforced-filesystem-sandbox.md): the write sandbox becomes tenant resolution inside the `DocumentStore` adapter rather than a path-prefix check.
- Per the carry-over noted in `.scratch/backfill/issues/07`, once the checkpointer is durable, **abandoning a cancelled run must explicitly clear its checkpoint thread** (both `thread_id = slug` and any `slug:stage` thread), or "a cancelled run starts clean" silently becomes "resume from the last checkpoint."
- A durable, shared run registry becomes possible, which is the prerequisite for running more than one uvicorn worker — the per-slug concurrency guard is currently process-local.

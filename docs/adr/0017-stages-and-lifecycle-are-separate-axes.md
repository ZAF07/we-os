# Pipeline stages and campaign lifecycle are separate axes

The operator UI names eight steps — `Brief · Research · Strategy · Plan · Produce · Approve · Publish · Measure` — against the engine's six stages. This is not a naming drift: the mockup conflated two different axes. Five of the eight are **stages** that produce a deliverable; three (`Approve`, `Publish`, `Measure`) are **campaign lifecycle status**, not pipeline steps.

The API speaks engine stages only. A separate `status` field carries the lifecycle (`draft` → `running` → `awaiting_approval` → `approved` → `published` → `measuring` → `archived`). Each stage additionally reports the operator **Phase** it belongs to, so the frontend renders its designed stepper without the engine adopting UI vocabulary — `Strategy` groups `brand-strategy` and `campaign-strategy`; `Produce` groups `creative-brief` and `asset-prompts`; `Brief` is the campaign goal, a Stage 0 input rather than a stage.

This resolves the open consequence parked in [ADR-0012](0012-nextjs-frontend-and-bff-in-monolith.md), which deferred the FE↔engine stage mapping until wiring time.

## Considered options

- **Flatten — expose all six engine stages 1:1** — rejected: simplest contract, but it changes the approved design and exposes internal vocabulary like `asset-prompts` to non-technical operators.
- **Rename engine stages to the operator vocabulary** — rejected: one vocabulary everywhere, but it collapses two genuinely distinct specialist stages into one and breaks the glossary, the guardrail filenames, the subagent contracts, and the `.claude/` layer.

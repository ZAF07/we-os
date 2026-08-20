# Channel and budget planning precedes creative

The pipeline is reordered so the Performance Plan is stage 4, before the Creative Brief:

```
research → brand-strategy → campaign-strategy → performance-plan → creative-brief → asset-prompts
```

Previously the creative brief and asset prompts were authored at stages 4–5 and the performance plan at stage 6, so creative was briefed without knowing which channels it would run on, and asset prompts were written without format specs, aspect ratios, or placement constraints — after which the performance agent selected channels for creative that was never scoped to them. The channel-and-spend decision was also being made twice: roughly at stage 3 by the Marketing Director, then properly at stage 6, downstream of the creative it should have informed.

Stage 3 keeps the strategic call (approach, rough channel mix); stage 4 makes it concrete (channel mix, spend allocation per channel, KPI targets, and the **format requirements** creative must satisfy); creative is then briefed against real placements. Post-launch analysis and optimization remain a separate operational loop.

Here "budget" means **media/ad spend** — the `Campaign budget` Required field in `templates/campaign-goal.md`, allocated per channel. Generation cost is a different concern entirely ([ADR-0020](0020-usage-ledger-and-enforced-quota.md)).

## Consequences

- Touches the stage order and prerequisite chain in `governance/pipeline.py`, the stage task text, and the creative-brief and performance-plan rubrics.
- Cheap now; expensive once the frontend and stored campaigns are bound to the current order.
- Matters most once assets are generated for real and published to Meta and TikTok, where a 9:16 TikTok video and a 1:1 Meta feed still are different briefs.

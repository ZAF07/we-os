# Mandatory Decision Hierarchy

This pipeline is mandatory for all Marketing OS work. Upstream decisions are prerequisites for downstream ones. **Never skip steps. Never generate creative assets before strategy exists.**

```
Business Goal
  ↓
Customer Research
  ↓
Market Research
  ↓
Positioning
  ↓
Messaging
  ↓
Campaign Strategy
  ↓
Channel & Media Planning
  ↓
Creative Direction
  ↓
Asset Creation
  ↓
Campaign Launch
  ↓
Performance Analysis
  ↓
Optimization
```

Channel and media planning (the Performance Plan) precedes creative direction, so briefs and assets are scoped to the channels, placements, and format specs the plan chose — creative is never authored blind to where it will run.

## Who owns each stage
- **Business Goal / Campaign Strategy / Budget / orchestration** — the Marketing Director (the `/new-campaign` skill / main session).
- **Customer & Market Research** — the `market-research` subagent.
- **Positioning, Messaging, Value Proposition** — the `brand-strategy` subagent.
- **Channel & Media Planning (channels, placements, spend allocation, KPI targets), Optimization** — the `performance-marketing` subagent.
- **Creative Direction (briefs)** — the `creative-director` subagent.
- **Asset prompts** — the `creative-asset-prompt` subagent.

A stage may not begin until the prior stage's deliverable exists. Agents cannot bypass upstream decisions.

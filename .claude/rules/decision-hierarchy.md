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

## Who owns each stage
- **Business Goal / Campaign Strategy / Budget / orchestration** — the Marketing Director (the `/new-campaign` skill / main session).
- **Customer & Market Research** — the `market-research` subagent.
- **Positioning, Messaging, Value Proposition** — the `brand-strategy` subagent.
- **Creative Direction (briefs)** — the `creative-director` subagent.
- **Asset prompts** — the `creative-asset-prompt` subagent.
- **Channels, KPIs, Budget detail, Optimization** — the `performance-marketing` subagent.

A stage may not begin until the prior stage's deliverable exists. Agents cannot bypass upstream decisions.

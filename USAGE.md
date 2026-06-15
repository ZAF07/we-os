# Using Marketing OS

Marketing OS produces sharp campaigns only when fed real customer truth. Feed it nothing specific and it returns generic garbage that fits any business and helps none. So the agent is **gated**: it will not start until you've given it a complete **Customer DNA** and a **campaign goal**. Do the prep first — it's the difference between a campaign and filler.

## Step 1 — Collect the Customer DNA

The Customer DNA is the stable, reusable profile of the business and its customers. Fill it **once** per customer; every future campaign reuses it.

```
cp templates/customer-dna.md customers/<name>/dna.md
```

Then fill it in with real, specific information. The agent **will not run** until every **Required** field is filled (not left as a `<...>` placeholder):

- **Business** — name, what they sell, category, price point
- **Customers** — primary segment(s); pain points / jobs-to-be-done
- **Differentiation** — why customers genuinely choose them
- **Reach & constraints** — geography/service area, language(s), budget range, hard constraints (legal, claims to avoid, brand no-gos)

Recommended (the more real detail, the sharper the output): competitors, brand voice & guardrails, current channels + what's worked/failed, proof points, common objections, baseline metrics.

> Be concrete. "Busy parents within 5km who want their kids active after school" beats "everyone who likes fitness." The agent can only be as specific as the DNA.

## Step 2 — Define the campaign goal

The goal is **per-campaign** (the DNA is shared across campaigns).

```
cp templates/campaign-goal.md campaigns/<slug>/goal.md
```

Required: one measurable business objective + timeframe, the campaign budget, the target segment (drawn from the DNA), and success metrics across all three tiers — **Business** (revenue/leads/bookings), **Marketing** (CTR/CPC/conversion), **Creative** (hook rate/watch time/engagement).

## Step 3 — Run the agent

```
/new-campaign <name>
```

`<name>` matches the customer folder (`customers/<name>/dna.md`). On start the agent runs a **gate**:

1. Loads the Customer DNA — missing? It stops and points you to the template.
2. Checks every Required DNA field is filled — incomplete? It lists exactly what's missing and stops.
3. Confirms the campaign goal — absent? It asks for it and stops.

**No delegation happens until the gate passes.** Once it does, the Marketing Director runs the mandatory pipeline — research → brand strategy → campaign strategy → creative direction → asset prompts → performance plan — delegating each stage to its specialist. Deliverables are written to `campaigns/<slug>/`.

## What "strictly abide by the DNA" means

Every recommendation the agents make must trace back to the Customer DNA or to research findings. They are instructed to refuse to produce generic, DNA-unsupported content, and to flag gaps rather than invent. If output ever feels generic, the fix is almost always a thinner DNA — enrich `customers/<name>/dna.md` and re-run.

## Required-fields checklist

**Customer DNA** — business name + what they sell · primary segment(s) · pain points / jobs-to-be-done · differentiation · geography + language · budget range + hard constraints.

**Campaign goal** — measurable objective + timeframe · budget · target segment · success metrics (Business / Marketing / Creative).

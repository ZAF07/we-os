# Performance Plan — Coast Coffee Launch

> **Agent:** Performance Marketing  
> **Date:** 2025-07-16 (revised 2025-07-16)  
> **Grounding:** Customer DNA (`customers/coast-coffee/dna.md`), Campaign Goal (`campaigns/coast-coffee-test-three/goal.md`), Campaign Strategy (`campaigns/coast-coffee-test-three/campaign-strategy.md`), Market Research (`campaigns/coast-coffee-test-three/research.md`), Creative Brief (`campaigns/coast-coffee-test-three/creative-brief.md`)  
> **Status:** Complete — performance plan is operationalised, with setup specifications, measurement cadence, and optimization decision trees. Creative copy and content specifications live in the Creative Brief; this document specifies formats, placements, requirements, and decision rules only.

---

## 0. Success Metrics First (Defined Before Channels or Spend)

> Per the operating principle: define success metrics across all three KPI tiers before recommending channels or allocating budget. **This section stands independently — no channel selection, budget figure, or spend allocation appears here.** Channels are selected in Section 1. Budget is allocated in Section 3. Both are derived from these targets, never the reverse.

### 0.1 Why These Targets

Every target below is traceable to the campaign's business objective (70 new customers in 8 weeks at blended CAC ≤ SGD 14). The cascade works backwards: the business KPI sets the ceiling; the marketing KPIs define the funnel thresholds needed to hit it; the creative KPIs define the engagement thresholds needed for the marketing KPIs to work. If any tier underperforms, the tier above it cannot be met.

These targets answer the question "What must be true for this campaign to succeed?" before anyone asks "How do we make it true?" or "What will it cost?"

### 0.2 KPI Cascade

```
BUSINESS KPI — 70 new customers, CAC ≤ SGD 14, AOV ≥ SGD 50
        ↑ depends on
MARKETING KPIs — Landing page CVR ≥ 3%, CPA ≤ SGD 25, CTR ≥ 1.0%
        ↑ depends on
CREATIVE KPIs — Hook rate ≥ 25%, engagement ≥ 4%, video completion ≥ 30%
```

### 0.3 The Numbers That Matter

| Tier | KPI | Target | Why This Number (Grounding) | Measured By |
|------|-----|--------|-----------------------------|-------------|
| **Business** | New customers (8 weeks) | 70 | Primary objective from Campaign Goal. Minimum viable cohort for retention analysis and repeat-purchase signal. | Shopify first-time buyer count |
| **Business** | Blended CAC | ≤ SGD 14 | At the DNA-confirmed price point (SGD 18–30/bag) and trio AOV target (~SGD 50), a CAC of SGD 14 preserves positive contribution margin on the first purchase. Essential for a bootstrapped DTC launch — no cross-subsidy from repeat purchases is assumed. | Total campaign spend ÷ new customers |
| **Business** | AOV | ≥ SGD 50 | Trio offer target from Campaign Goal. If AOV < SGD 40, the trio is being bypassed and unit economics degrade — single-bag purchases at SGD 18–30 produce thinner margins at the same CAC. | Total revenue ÷ total orders |
| **Marketing** | Landing page CVR | ≥ 3% | DTC food/beverage benchmark range is 2–5%. 3% is the conservative-achievable floor for a differentiated offer with a clear value proposition. Below 2% signals a trust or offer clarity problem independent of which channels drive traffic. | Shopify analytics (session → purchase) |
| **Marketing** | CPA (paid acquisition) | ≤ SGD 25 | Derived from the CAC ceiling and the DNA price point: at SGD 25 CPA and SGD 50 AOV, paid acquisition contributes positively after COGS. This is the ceiling — above SGD 25, paid becomes contribution-negative on first purchase and the blended CAC target can only be met if organic channels dramatically overperform. | Ad platform (Purchase event) |
| **Marketing** | CTR (paid social) | ≥ 1.0% | Singapore F&B benchmark for social advertising. The DNA's differentiation pillars (freshness proof, Asian origin, tier system) should outperform generic coffee advertising. Below 0.8% signals the creative hook isn't working — regardless of which platform carries it. | Ad platform (CTR all) |
| **Marketing** | Organic profile conversion (visit → link click) | ≥ 20% | Measures whether the Instagram profile converts curiosity into site traffic. High profile visits with low clicks signals a bio or link problem — the organic trust layer isn't functioning. | Instagram Insights |
| **Creative** | Hook rate (3-sec / thumb-stop) | ≥ 25% | First 3 seconds must stop the scroll. The vacuum-sealing visual + "fresh beans by mail" is inherently curiosity-driving. Grounded in the DNA's freshness differentiation — if this doesn't stop scrolls, the brand's strongest visual asset isn't landing. | Ad platform (3-sec video views ÷ impressions) |
| **Creative** | Engagement rate (organic) | ≥ 4% | Signals audience-product fit beyond paid distribution. Organic engagement is a leading indicator of whether the content resonates with the target segment before any money is spent amplifying it. | Instagram Insights (engagement ÷ reach) |
| **Creative** | Video completion rate (50%) | ≥ 30% | Trust-build and offer live in the second half of video creative. Drop-off before the CTA means the ad hooks but doesn't close — a creative structure problem, not a channel problem. | Ad platform (50% video views ÷ impressions) |
| **Creative** | Carousel swipe-through (to card 3) | ≥ 60% | Each card maps to a tier. Swipe-through signals the curation story is compelling across the full narrative arc. Applies regardless of where the carousel runs. | Ad platform (carousel card metrics) |

> **Note:** Market-rate diagnostics such as CPM benchmarks (e.g., Singapore Meta Ads SGD 8–15) are addressed in the Budget section (§3.3), where they inform impression-volume calculations. They are not KPI targets and do not belong in this section — CPM is an input cost, not a success metric.

---

## 1. Channel Selection

### 1.1 Channel Roster

| Channel | Role | Weight | Why This Channel (DNA-Grounded Rationale) |
|---------|------|--------|-------------------------------------------|
| **Meta Ads (Instagram Reels + Facebook Feed)** | Primary paid acquisition | 80% of budget (SGD 800) | Highest reach-per-dollar for Singapore DTC at small budgets. Interest targeting reaches home baristas (V60, Aeropress, specialty coffee, home espresso). Reels format suits the visual proof (vacuum-sealing, beans, tiers). The DNA's primary segment — Singapore home baristas 25–44 — over-index on Instagram. |
| **Instagram Organic** | Brand presence + social proof | No media spend; content + time investment | The account is the "check us out" destination when people search the brand after seeing an ad. For a new brand with zero trust equity (DNA: brand maturity = WEAKNESS, Research §2.2), the organic feed is the trust-verification layer. Expected contribution: 10–15 customers via organic referral. |
| **Micro-Influencer Seeding** | Trust transfer + reach | 12% of budget (SGD 120, product cost only) | DNA Gap: no customer testimonials. Research Gap #5: no social proof. 3–5 Singapore home-brewing creators receive the trio and produce honest review content. Creators transfer their established trust to Coast Coffee. At SGD 30 per creator (beans + delivery), this is the highest-leverage trust-building spend available. Expected contribution: 10–15 customers. |
| **Coffee Community / Word of Mouth** | Amplification | No media spend; participation effort | Singapore has active specialty coffee communities (Homeground Coffee Club, Kopi, Reddit r/singapore, Carousell coffee groups). Organic presence + early customer word-of-mouth drives discovery. Not a paid channel — presence and responsiveness. Expected contribution: 5–10 customers. |

### 1.2 Channels Explicitly Excluded

| Channel | Why Excluded | Condition to Revisit |
|---------|-------------|---------------------|
| **Google Search Ads** | At SGD 125/week, budget too thin to compete on "specialty coffee beans Singapore" against established roasters with higher CPC bids and Quality Scores. Search intent exists but CPCs will consume budget without sufficient conversion volume. | When monthly budget ≥ SGD 1,000, test brand-term search + a small "Asian specialty coffee" long-tail campaign. |
| **TikTok Organic** | Valid channel, but requires 3–5 posts/week sustained over months to gain algorithmic traction. Coast Coffee has no existing content library. Included as secondary organic channel if the team has capacity; not a primary dependency for the 70-customer goal. | If Instagram organic performs well and content library builds, repurpose Reels to TikTok in Week 5+. |
| **Email** | No existing list (new brand). Email becomes relevant post-launch for retention and repeat purchases. | After 50+ customers acquired, set up a post-purchase flow and a basic newsletter for repeat buyers. |
| **Shopee / Lazada** | Marketplace dilutes the DTC brand experience and the curation narrative. The tier system needs its own landing page to explain. Marketplace commissions (5–8%) also compress already-thin margins. | Future channel for scale; not a launch channel. |
| **Programmatic Display / YouTube** | CPMs too high relative to budget. Insufficient frequency to build brand recall at SGD 125/week. | Not relevant at this budget tier. |

### 1.3 Channel Contribution Model (How 70 Customers Are Reached)

```
                         70 NEW CUSTOMERS
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   PAID (Meta Ads)       ORGANIC               COMMUNITY
   35–45 customers       + SEEDING             + WORD OF MOUTH
   SGD 800 spend        20–30 customers       5–10 customers
        │                     │                     │
   ┌────┴────┐          ┌────┴────┐          ┌────┴────┐
   │         │          │         │          │         │
  Hero     Carousel   Instagram  Influencer  Coffee    Early
  Video    Retarget    Organic    Content    Groups    Customer
  25–30    5–10        10–15      10–15      3–5       Referrals
                                                   2–5
```

**Why this split is realistic:**
- Paid contribution of 35–45 customers at SGD 800 spend requires CPA of SGD 17.80–22.90 — achievable at a 3% landing page CVR and 1% CTR (see §3.3 math).
- Organic + seeding contribution of 20–30 assumes modest but real traction: 4 influencer posts at ~1,500 average reach each = ~6,000 impressions. At 0.5% conversion to site visit and 3% site CVR = ~1 customer per creator. Realistically, some creators overperform; organic compounds over 8 weeks.
- Community + WOM is conservative — 5–10 customers across 8 weeks is ~1/week. This is a floor, not a ceiling.

---

## 2. Campaign Setup Specifications

### 2.1 Meta Ads Campaign Architecture

#### 2.1.1 Pre-Launch Requirements (Do Not Launch Paid Without These)

| Requirement | Owner | Verification |
|-------------|-------|--------------|
| **Meta Pixel installed** on landing page | Coast Coffee / tech | Test with Meta Pixel Helper browser extension. Confirm PageView, ViewContent, AddToCart, and Purchase events fire correctly. |
| **Purchase event firing** | Coast Coffee / tech | Run a test purchase through the full checkout flow. Confirm the Purchase event appears in Meta Events Manager with correct value and currency (SGD). |
| **CAPI (Conversions API) configured** | Coast Coffee / tech | If using Shopify, install the Meta Shopify integration. CAPI is recommended alongside the browser Pixel for more reliable conversion tracking. At minimum, browser Pixel must work. |
| **Landing page live** | Coast Coffee / tech | The trio offer page is published, loads correctly on mobile, and checkout functions. |
| **Domain verified** in Meta Business Suite | Coast Coffee / tech | Required for aggregated event measurement and campaign optimisation. |
| **Ad account spend limit** | Coast Coffee | Confirm the ad account has no daily spend limit below SGD 25/day. |

**Why these are non-negotiable:** Without the Pixel and Purchase event, Meta cannot optimise for conversions — the campaign defaults to link clicks or traffic, which will burn budget with no conversion data. The campaign strategy's entire Phase 2–3 optimisation plan depends on conversion data existing.

#### 2.1.2 Campaign Structure

```
CAMPAIGN: Coast Coffee — Launch — Conversions
Objective: Conversions (Purchase event)
Campaign spending limit: SGD 800 (lifetime)
Buying type: Auction
Bid strategy: Highest Volume (auto-bid, no cost cap initially)

├── AD SET 1: Broad Interest — Home Baristas
│   Conversion event: Purchase
│   Budget: SGD 60/week (Weeks 1–2), SGD 80/week (Weeks 3–6), SGD 50/week (Weeks 7–8)
│   Attribution window: 7-day click + 1-day view
│   Audience:
│     - Location: Singapore (living in or recently in)
│     - Age: 25–44
│     - Gender: All
│     - Languages: English (All)
│     - Detailed targeting (interest-based):
│       - Interests: Specialty coffee, Coffee preparation, Pour-over coffee, 
│         Espresso, Coffee roasting, Homebrewing coffee, Single-origin coffee,
│         Aeropress, French press, Chemex, Hario, V60
│       - OR Interests: Coffee (beverage), Coffee culture, Third-wave coffee
│       - Narrow further: Must also match — Online shopping, E-commerce, 
│         Food delivery (to capture DTC-buying behaviour)
│     - Estimated audience size target: 150,000–300,000 (broad enough for 
│       learning, tight enough for relevance)
│   Placements:
│     - Instagram Reels (primary — highest engagement format for F&B discovery)
│     - Instagram Stories (secondary)
│     - Instagram Feed (tertiary — static formats)
│     - Facebook Feed (secondary)
│     - Facebook Reels (secondary)
│     - Exclude: Audience Network, Right Column, Marketplace, In-stream video
│       (low-intent placements that dilute CVR)
│   Ads: 2 video variants (see §2.1.4 for format requirements) — split test
│
├── AD SET 2: Retargeting — Video Viewers + Site Visitors
│   Status: PAUSED until pool ≥ 1,000 (activate ~Week 3–4)
│   Conversion event: Purchase
│   Budget: SGD 30/week (activated when pool reaches threshold)
│   Attribution window: 7-day click + 1-day view
│   Audience (custom audience):
│     - Video viewers: Watched ≥50% of either hero video variant in last 30 days
│     - OR Website visitors: Visited landing page in last 14 days 
│       (exclude purchasers in last 30 days)
│   Placements: Same as Ad Set 1
│   Ads: Carousel ad (see §2.1.4) + 1 static flat-lay format
│
└── AD SET 3: Lookalike — Purchaser Seed
    Status: PAUSED until ≥100 purchasers via Meta Pixel (~Week 6+)
    Conversion event: Purchase
    Budget: SGD 40/week (activated when seed audience reaches threshold)
    Audience: 1–3% Lookalike of Purchase event custom audience (last 60 days)
    Placements: Same as Ad Set 1
    Ads: Best-performing creative from Ad Set 1
```

#### 2.1.3 Why This Structure

| Decision | Why |
|----------|-----|
| **Conversions objective (not Traffic)** | At SGD 125/week, the algorithm needs to optimise for what matters — purchases. Traffic campaigns may generate cheap clicks but will not learn who buys. |
| **Highest Volume bidding (not Cost Cap)** | With no conversion history, a cost cap at SGD 25 would likely prevent the ad set from exiting the learning phase. Start with auto-bid to gather data; introduce a cost cap in Phase 2 (Week 3) if CPA is stable. |
| **Broad interest targeting (not hyper-niche)** | At this budget, hyper-niche targeting (e.g., "V60 owners only") produces audience pools too small for the algorithm to learn from. Interest layering (coffee + DTC behaviour) balances relevance with adequate pool size. |
| **Two ad variants from launch** | Produces comparative data on which hook (freshness vs. curation) drives more purchases. The loser is paused by end of Week 2. This is the highest-value test at the lowest cost. |
| **No Audience Network, Right Column, Marketplace** | These placements produce cheap impressions but abysmal conversion rates. For a Conversion-optimised campaign, they waste budget on low-intent views. The campaign strategy is explicit: every impression must have a chance to convert. |
| **Retargeting gated behind 1,000-person pool** | Below 1,000, retargeting audiences are too small to deliver consistent frequency or statistically meaningful conversion data. The budget is better spent on prospecting until the pool builds. |

#### 2.1.4 Creative Format & Placement Requirements

> Ad copy, headlines, CTAs, and creative concepts for each asset are specified in the Creative Brief (`campaigns/coast-coffee-test-three/creative-brief.md`, §3–6). This section specifies only the format, placement, and performance requirements each asset must satisfy to function in the campaign architecture above.

| Asset | Format | Placement | Performance Requirement | Creative Brief Reference |
|-------|--------|-----------|------------------------|--------------------------|
| **Hero Video — Variant A** (Freshness Hook) | 9:16 vertical, 1080×1920px, 25–30 sec, H.264, AAC audio. Captions burned in (not auto-generated). Sound design must register at low volume. | Ad Set 1 (all placements), Instagram Organic feed | Must carry a distinct hook in the first 3 seconds (freshness/proof angle). Must include the trio offer CTA in the final 5 seconds. | Creative Brief §3.3–3.4 (A1) |
| **Hero Video — Variant B** (Alternative Hook) | Same specs as Variant A. | Ad Set 1 (split-test alongside Variant A) | Must carry a distinct hook in the first 3 seconds that differs from Variant A (curation/system angle). Identical body/CTA to Variant A from scene 0:03 onward to isolate hook performance. | Creative Brief §3.4 (A2) |
| **Carousel Ad** | 1:1 square, 1080×1080px per card, 3–4 cards. Each card must work as a standalone image. Final card is the CTA card. | Ad Set 2 (retargeting, Week 3+), Ad Set 1 (secondary, Week 3+) | Cards must communicate the tier system sequentially. Swipe-through to card 3 target: ≥ 60%. | Creative Brief §5.1, §6.1 (A3) |
| **Static Flat-Lay (Trio Product Shot)** | 1:1 square, 1080×1080px. Clean, well-lit product photography. | Ad Set 2 (retargeting, secondary), potentially Ad Set 1 if carousel underperforms | Functions as a direct offer reminder for retargeting audiences who already understand the tier system from the video. | Creative Brief §6.1 (A10) |

**Creative requirements all assets must satisfy (per Creative Brief §2.1, §9):**
- Lead with process proof, not adjectives. Show the vacuum seal, degassing, the six-week number.
- The three tier bags (amber / jade / indigo) must be visually distinct and recognisable.
- All video assets: captions burned in for sound-off viewing.
- All assets: trio offer must be clear; CTA must be unambiguous.

### 2.2 Instagram Organic Setup

#### 2.2.1 Profile Pre-Launch Checklist

| Element | Specification | Why |
|---------|---------------|-----|
| **Profile photo** | Coast Coffee logo or the "≥6 WEEKS FRESH" stamp as icon | Logo for recognition; stamp as an alternative if the logo is not finalised. The stamp is the most distinctive visual asset. |
| **Bio** | Must communicate all three positioning pillars (curation/tier system, Asian origins, freshness guarantee) and include a directional cue to the trio offer link. ≤ 150 characters. Creative Brief §4.2 provides the campaign theme expression for this touchpoint. | The bio is the first text a profile visitor reads — it must carry the full value proposition in one glance. |
| **Link in bio** | Landing page (trio offer) — use a link-in-bio tool (Linktree, Beacons, or native) if multiple destinations are needed later | Single destination at launch = less friction. |
| **Story Highlights (pre-populated)** | Minimum 4 covers before the first organic post: (1) The Tiers, (2) Freshness Process, (3) Origins, (4) Delivery/FAQ. Content for each lives in the Creative Brief §5.1. | A new brand's profile looks empty. Pre-populated Highlights with process content signal an active, legitimate brand before the first organic post goes live. |
| **Pinned posts (3)** | Before launch: tier explainer, process/freshness post, and trio product shot pinned as the top 3 grid posts. Specific assets: see Creative Brief §5.2 (content calendar) and §6.1 (asset inventory). | First-time profile visitors see curated proof, not an empty feed. Pins are the brand's "about us" for people who check after seeing an ad. |

#### 2.2.2 Posting Cadence

> Specific content topics, asset IDs, and creative direction for each post live in the Creative Brief §5.2 (Organic Content Calendar). This section specifies frequency and format mix only.

| Week | Posts/Week | Format Mix | Content Pillar Focus |
|------|-----------|------------|---------------------|
| **Pre-launch** | Populate 6–9 posts | Mix of reels, statics, carousels | Tier explainers, process, origins, trio product shot |
| **1–2** | 3 posts/week | 1 reel + 1 static + 1 story sequence per week | Trust + Freshness (lead), Trust + Curation (secondary) |
| **3–4** | 3 posts/week | 1 reel + 1 static + 1 story per week | Differentiation + Story (origins), reshared influencer content |
| **5–6** | 2–3 posts/week | 1 reel + 1–2 statics per week | Community content, early customer reposts, pillar remixes |
| **7–8** | 2 posts/week | Sustain cadence; reshare best performers | Best-performing content; testimonial reposts |

**Why 3 posts/week and not daily:** At 3/week, the feed stays active without exhausting the content library. A new brand posting daily with thin content looks desperate. Quality and specificity matter more than volume for trust-building (DNA: trust is the binding constraint). The strategy's "Proof, Not Promise" principle applies to posting frequency — 3 well-produced posts that show the process beat 7 filler posts that make claims.

### 2.3 Micro-Influencer Seeding Setup

#### 2.3.1 Creator Selection Criteria

| Criterion | Threshold | Why |
|-----------|-----------|-----|
| **Follower range** | 2,000–15,000 | Nano/micro creators have higher engagement rates (3–8%) than macro creators. Their audiences trust their recommendations more. At this budget, macro creators are unaffordable and unnecessary. |
| **Content niche** | Home brewing, specialty coffee, Singapore food/drink | Must overlap with the target segment. A general lifestyle creator with no coffee content will produce inauthentic posts. |
| **Posting consistency** | Minimum 3 posts/week on feed or Reels | Creators who post regularly have active, engaged audiences. Inactive creators have dormant followings — reach will be suppressed. |
| **Engagement rate** | ≥ 3% (authentic, not engagement-pod-driven) | High engagement signals a real community. Check for comment quality — "nice post 🔥" spam suggests pod activity. |
| **No competing coffee partnerships** | No active partnership with another Singapore roaster in the last 3 months | Avoids conflict of interest and audience confusion. |
| **Personality fit** | Genuine, curious, not performatively snobby | The Curator archetype should feel natural to them. Gatekeeping coffee creators will alienate Safe Brewers (Segment A). |

**Suggested creator types (4 creators):**
1. **The Home Barista Educator** — posts brewing tutorials, gear reviews, tasting notes. Audience: Segments A + B.
2. **The Singapore Food Explorer** — posts food/drink discoveries, local hidden gems. Audience: Segments B + D.
3. **The Aesthetic Home Brewer** — posts beautiful pour-over videos, morning rituals, coffee station setups. Audience: Segments A + C.
4. **The Curious Coffee Nerd** — posts origin deep-dives, processing experiments, comparative tastings. Audience: Segments B + C.

#### 2.3.2 Creator Brief (Operational Template)

> This is the process for engaging creators. Creative direction for what to highlight lives in the Creative Brief §8. The message below is an operational template — not ad copy.

**Brief message:**

"Hi [name] — we're Coast Coffee, a new Singapore specialty coffee brand focused on Asian-origin beans. We've put together a 3-tier flavour system (safe → adventurous) so home baristas can pick by preference instead of guessing.

We'd love to send you our Flavour Trio — one bag from each tier — for an honest review. No script. No mandatory talking points. Brew them, taste them, share what you actually think with your audience.

What's in the box:
- Tier 1: Safe & Balanced — familiar flavours, clean, easy-drinking
- Tier 2: Complex & Floral — the sweet spot between familiar and adventurous
- Tier 3: Exciting & Unknown — something unusual

All our beans are degassed 48 hours after roasting, then vacuum-sealed with a 6-week freshness guarantee.

If you'd like to try it, DM us your address. We'll get it to you this week."

**Why this brief works:**
- "Honest review. No script." signals respect for the creator and their audience — the trust transfer only works if the review is genuine.
- The tier names and explanations are provided for accuracy, not as talking points.
- The freshness process is stated factually (degassed → vacuum-sealed → 6 weeks) — the creator will see the vacuum seal themselves and likely mention it organically.
- ASK is low (DM address, free product) — no complex negotiation at this budget.

#### 2.3.3 Seeding Timeline

| Week | Action |
|------|--------|
| **Pre-launch** | Identify and DM 6–8 creators (expect 3–5 to accept). Confirm addresses. |
| **Week 1** | Dispatch trio packs. |
| **Week 2–3** | Creators receive, brew, and post (natural timeline). |
| **Week 3–4** | Reshare best creator content to Coast Coffee's Instagram (Stories + feed with permission). If a post performs exceptionally, boost with SGD 20–40 from reserve. |

---

## 3. Budget Allocation

*All budget figures below are derived from the KPI targets in Section 0. The targets set the bar; the budget is the fuel. No spend figure appears before this section.*

### 3.1 Total: SGD 1,000

| Line Item | Allocation | % | Rationale (DNA-Grounded) |
|-----------|-----------|----|--------------------------|
| **Meta Ads (paid social)** | SGD 800 | 80% | The engine. Only channel with targeting precision + sufficient reach at this budget. Singapore home baristas discover new coffee brands on Instagram (Research §3.2: Social/Cultural — Instagram and TikTok are dominant discovery platforms). |
| **Micro-influencer seeding** | SGD 120 | 12% | 4 creators × ~SGD 30 cost per trio (beans + packaging + delivery). This is product cost, not media spend. At SGD 30/creator, it is the single highest-leverage trust-building investment — each creator post costs less than 2 days of Meta Ads and produces content with embedded social proof. |
| **Reserve / contingency** | SGD 80 | 8% | Held for Week 4 reallocation: if Meta overperforms (CPA < SGD 18), shift reserve into scaling the winner. If seeding generates strong UGC, boost top-performing creator posts with SGD 20–40 each. If Meta underperforms, the reserve prevents the campaign from riding a losing horse for 8 weeks. |

### 3.2 Meta Ads Allocation — Phase Detail

| Phase | Weeks | Weekly Spend | Total | Daily Equivalent | Objective |
|-------|-------|-------------|-------|-----------------|-----------|
| **Phase 1: Launch + Learn** | 1–2 | SGD 100 | SGD 200 | ~SGD 14/day | Gather conversion data. Identify which hook variant performs. Let the algorithm exit the learning phase (~50 conversions). |
| **Phase 2: Optimise** | 3–6 | SGD 115 | SGD 460 | ~SGD 16/day | Shift budget to winning hook variant. Activate retargeting (if pool ≥ 1,000). Introduce carousel ad. Narrow audiences based on Phase 1 data. |
| **Phase 3: Close** | 7–8 | SGD 70 | SGD 140 | ~SGD 10/day | Retargeting-dominant. Social proof angle if customer content exists. Spend drops as organic + WOM carry weight. Concentrate remaining budget on highest-ROAS audience segments. |

### 3.3 Expected Paid Economics (The Math)

The CPM benchmark for Singapore Meta Ads (F&B, coffee interest) is typically SGD 8–15. This is a market-rate input, not a KPI target — it informs impression-volume estimates below.

| Metric | Calculation / Assumption | Result |
|--------|--------------------------|--------|
| **Total Meta spend** | As allocated | SGD 800 |
| **Estimated CPM (SG, coffee interest)** | SGD 8–15 (Meta benchmark for Singapore F&B) | SGD 12 (midpoint) |
| **Estimated impressions** | SGD 800 ÷ SGD 12 × 1,000 | ~66,700 |
| **Estimated clicks (at 1% CTR)** | 66,700 × 0.01 | ~667 |
| **Estimated landing page visits (95% of clicks)** | 667 × 0.95 | ~634 |
| **Estimated purchases (at 3% CVR)** | 634 × 0.03 | ~19 |
| **Estimated purchases (at 4% CVR)** | 634 × 0.04 | ~25 |
| **Estimated purchases (at 5% CVR)** | 634 × 0.05 | ~32 |
| **CPA range** | SGD 800 ÷ purchases | SGD 25–42 |

**Why these are estimates, not guarantees:** The campaign launches with zero conversion data. Meta's algorithm requires ~50 conversion events to exit the learning phase. Until then, CPA will be volatile. The scenarios below model how performance can diverge based on the two most sensitive variables — CTR and CVR.

| Scenario | Impressions | CTR | Clicks | CVR | Purchases | CPA | Likelihood |
|----------|------------|-----|--------|-----|-----------|-----|------------|
| **Below floor (stop-loss triggered)** | 25,000 (CPM SGD 16, high competition) | 0.7% | 175 | 1.5% | 3 | SGD 67+ | Low — requires three variables to underperform simultaneously. Triggers the Week 2 stop-loss (see below). |
| **Realistic floor** | 50,000 (CPM SGD 14) | 0.9% | 450 | 2.5% | 11 | SGD 73 | Moderate — below-target CVR and CTR in combination. Still produces signal. |
| **Conservative** | 60,000 (CPM SGD 13.33) | 1.0% | 600 | 3.0% | 18 | SGD 44 | Moderate — meets CTR floor but CVR at low end of acceptable range. |
| **Baseline (target)** | 66,700 (CPM SGD 12) | 1.2% | 800 | 4.0% | 32 | SGD 25 | The plan. Requires creative and landing page to perform at target. |
| **Optimistic** | 80,000 (CPM SGD 10) | 1.5% | 1,200 | 5.0% | 60 | SGD 13 | Requires all variables to overperform. |

#### Stop-Loss Rule (Non-Negotiable)

> **If, after SGD 200 spent (end of Week 2), Meta Ads have delivered fewer than 5 purchases OR CPA exceeds SGD 50, pause all Meta spend immediately.** This stop-loss is embedded in the Week 2 Phase Gate (§5.4).

**If the stop-loss triggers:**
1. Pause all Meta ad sets. Do not spend another dollar on paid social until the bottleneck is diagnosed.
2. Diagnose root cause using the decision tree in §5.3:
   - If CVR ≥ 2.5% but CTR < 0.8% → creative hook problem. Produce revised hook variant(s) before reactivating.
   - If CTR ≥ 0.8% but CVR < 2.5% → landing page or offer problem. Fix the page before reactivating.
   - If both CVR and CTR are below threshold → both creative and page need revision. Redirect budget (see step 3).
3. **Redirect remaining SGD 600 budget:**
   - SGD 350 → expanded influencer seeding (6–8 additional creators at ~SGD 40–50 each for product + delivery). The trust-transfer mechanism of authentic reviews bypasses the creative hook and landing page trust problems simultaneously.
   - SGD 150 → boost best-performing organic and creator content (amplify what's already resonating).
   - SGD 100 → reserve for opportunistic spend if a creator post goes viral or an organic post overperforms.
4. If Meta is fixed and reactivated later (Week 4+), allocate no more than SGD 200 from the remaining reserve — the redirected budget stays in organic/seeding channels which have become the primary acquisition engine.

**Why this stop-loss exists:** The realistic-floor scenario (CPA SGD 73 at SGD 800 total spend) would produce ~11 paid customers. Continuing to spend the full SGD 800 in that scenario wastes SGD 600 that could acquire more customers through seeding and organic amplification. The stop-loss converts a bad projection into a decision: at SGD 200, the campaign has enough data to know whether paid is viable. If it isn't, the budget pivots to channels that don't depend on creative hook performance.

**Key dependencies for paid performance:**
1. **The creative quality is existential** — hook rate and CVR are not nice-to-haves; they determine whether paid achieves its contribution.
2. **The landing page must convert** — if CVR is below 3%, every other KPI is irrelevant. The Week 2 CVR audit (see §5.2) is the most important decision point in the campaign.
3. **Organic + seeding contribution is not optional** — at baseline paid performance (32 customers), the campaign needs 38 customers from organic/seeding/community to hit 70. These channels are not supplementary; they are load-bearing.

---

## 4. Measurement & Tracking Plan

### 4.1 What Gets Measured, When, and By Whom

| Frequency | Metrics Reviewed | Source | Action Trigger |
|-----------|-----------------|--------|----------------|
| **Daily (5 min)** | Ad spend, impressions, clicks, CTR, link clicks, purchases (Meta), site sessions (Shopify) | Meta Ads Manager + Shopify dashboard | Spend pacing check. If daily spend exceeds SGD 20/day in Phase 1 without conversions, pause and investigate Pixel. |
| **Weekly (20 min)** | All three KPI tiers. A1 vs. A2 performance. Hook rate, video completion, CVR, CPA, AOV. | Meta Ads Manager + Shopify analytics + Instagram Insights | Compare against KPI targets in §0.3. Flag any metric below threshold for the next optimization cycle. |
| **Bi-weekly / Phase Review (Week 2, 4, 6)** | Full funnel: impression → click → visit → ATC → purchase. Segment by ad set, placement, creative variant. Organic contribution estimate. | All sources + manual calculation | Major reallocation decisions. Phase transition go/no-go (see §5.4 decision tree). |
| **End of campaign (Week 8)** | Final count: new customers, blended CAC, AOV, CPA by channel. Repeat purchase rate (early signal). Segment analysis. | All sources | Post-campaign report. Learnings for next campaign. |

### 4.2 Attribution Notes

**Challenge:** At this budget, the campaign will not have statistically significant multi-touch attribution data. Meta will claim more conversions than actually occurred (view-through attribution is generous). Shopify will capture the ground truth.

**Approach:**
- **Primary conversion counting:** Shopify first-time buyer count. This is the source of truth for the 70-customer business KPI.
- **Meta-reported purchases:** Use as a directional signal for optimization, not as the final count. Expect Meta to over-report vs. Shopify by 10–30%.
- **Organic attribution:** Use UTM parameters on the Instagram bio link (`utm_source=instagram&utm_medium=organic&utm_campaign=coast-launch`). Track organic conversions in Shopify.
- **Influencer attribution:** Provide each creator with a unique discount code (e.g., CREATORNAME5 for SGD 5 off). This tracks which creator drives purchases. The code also gives the creator's audience a reason to act.

### 4.3 UTM Convention

All paid and organic links use this structure:

```
Paid Meta Ads:
  ?utm_source=meta&utm_medium=paid&utm_campaign=coast-launch&utm_content=<asset_id>

Organic Instagram:
  ?utm_source=instagram&utm_medium=organic&utm_campaign=coast-launch

Influencer (link in their bio/story):
  ?utm_source=instagram&utm_medium=influencer&utm_campaign=coast-launch&utm_content=<creator_name>
```

---

## 5. Optimization Decision Tree

### 5.1 Creative Optimization — Hook Rate

```
Hook Rate (3-sec video views ÷ impressions)
│
├─ ≥ 30% → EXCELLENT. The hook is working. Do not touch it.
│          Consider testing a longer-form version (45–60 sec) for 
│          engaged audiences in Phase 2.
│
├─ 25–29% → ON TARGET. Continue monitoring. If video completion 
│            rate is also healthy (≥30%), the full ad is working.
│
├─ 20–24% → BELOW TARGET. The hook is underperforming. Action:
│            - By Week 2: If both video variants are in this range, 
│              brief a third hook variant drawing from an alternative 
│              brand strategy pillar (see Creative Brief §3.4 for the 
│              hook variant framework).
│            - If only one variant is weak, pause it and shift 
│              budget to the winner.
│
└─ < 20% → CRITICAL. The creative is not stopping scrolls. 
           Pause spend on underperforming variant immediately.
           Do not scale spend until a new hook is tested.
           Root cause possibilities:
           - Opening visual is not arresting enough (too static, 
             too dark, too generic)
           - Text overlay is too small for sound-off viewing
           - The hook doesn't create curiosity
           Refer to Creative Brief §3.4 for alternative hook angles.
```

### 5.2 Landing Page CVR Optimization

```
Landing Page CVR (sessions → purchases)
│
├─ ≥ 5% → EXCEPTIONAL. The offer and page are resonating.
│          Document what's working for future campaigns.
│
├─ 3.0–4.9% → ON TARGET. Continue monitoring. Look for 
│              segment-level patterns (which traffic source 
│              converts best).
│
├─ 2.0–2.9% → BELOW TARGET. Audit the page before scaling spend.
│              Check (in order of impact):
│              1. Is the trio offer explained above the fold?
│              2. Is the freshness guarantee visible without scrolling?
│              3. Is the pricing clear (SGD 50–54, not hidden)?
│              4. Is the CTA button obvious and above the fold on mobile?
│              5. Is checkout friction low? (Guest checkout available?
│                 PayNow offered? How many steps to complete?)
│              6. Are page load times < 3 seconds on mobile?
│              Fix the highest-impact issue before Week 3.
│
└─ < 2.0% → CRITICAL. The page is killing conversions. 
            Do not increase Meta spend. Allocate Week 3 entirely 
            to page fixes. Possible issues:
            - Trust signals absent (no freshness proof visible, 
              no vacuum-seal imagery, no guarantee language)
            - The trio offer is confusing (customers don't understand 
              what they're getting)
            - Technical issue (checkout broken, Pixel not firing, 
              slow load)
            - Price shock (SGD 50 is above impulse-buy threshold 
              for a new brand)
            Consider adding: a "What's in the Trio" section, a 
            freshness process diagram, and an FAQ addressing the 
            DNA objections directly.
```

### 5.3 CPA Optimization

```
Meta CPA (cost per Purchase event)
│
├─ ≤ SGD 18 → EXCEPTIONAL. Consider cautiously increasing 
│             daily spend by 15–20% to capture more volume.
│
├─ SGD 19–25 → ON TARGET. Maintain spend. Focus on audience 
│              refinement — which interest groups drive the 
│              lowest CPA?
│
├─ SGD 26–35 → ABOVE TARGET. Do not increase spend. 
│              Investigate:
│              - Is CVR healthy but CTR low? → Creative problem.
│                Fix the hook or test new creative.
│              - Is CTR healthy but CVR low? → Landing page or 
│                offer problem. Fix the page.
│              - Is CPM unusually high (>SGD 18)? → Audience 
│                competition problem. Broaden targeting or shift 
│                to a different interest cluster.
│
├─ SGD 36–50 → HIGH. The paid channel is struggling. 
│              Apply the same diagnostic as above but with 
│              urgency. Do not increase spend. Prepare the 
│              stop-loss redirect (see §3.3) if CPA does not 
│              improve by the Week 2 gate.
│
└─ > SGD 50 → STOP-LOSS TRIGGERED. Pause Meta spend. 
             Apply the stop-loss rule in §3.3: diagnose root 
             cause, fix the bottleneck, and redirect budget 
             to seeding + organic amplification. Meta may be 
             reactivated later (Week 4+) only if the bottleneck 
             is resolved and a revised creative is ready.
```

### 5.4 Phase Transition Decision Gates

```
PRE-LAUNCH GATE:
├─ Pixel firing Purchase events? → YES → Launch Phase 1
└─ NO → Do not launch. Fix Pixel.

WEEK 2 GATE (Phase 1 → Phase 2):
├─ ≥ 5 purchases tracked in Meta? → YES → Proceed to Phase 2
│   ├─ CTR ≥ 1.0%? → YES → Scale winning creative
│   └─ CTR < 1.0%? → Revise creative hook before scaling
├─ 1–4 purchases → CPA check:
│   ├─ CPA ≤ SGD 50? → Extend Phase 1 by 1 week. Monitor closely.
│   │   If CPA improves to ≤ SGD 35 by end of Week 3, proceed to Phase 2.
│   │   If CPA remains > SGD 35, trigger stop-loss (§3.3).
│   └─ CPA > SGD 50? → STOP-LOSS. Pause Meta. Redirect per §3.3.
└─ 0 purchases → CRITICAL. Stop spend. Audit Pixel, page, and checkout.

WEEK 4 GATE (Mid-Point):
├─ ≥ 30 total customers (all channels)? → ON TRACK. Proceed as planned.
│   ├─ Meta CPA ≤ SGD 25? → Maintain paid strategy.
│   └─ Meta CPA > SGD 25 but organic + seeding overperforming? → 
│       Reduce Meta spend, shift to seeding + community.
├─ 20–29 customers → BEHIND. Reforecast. 70 in 8 weeks still possible 
│   if organic accelerates (compounding effect of content library + 
│   word of mouth). Deploy reserve to best-performing channel.
└─ < 20 customers → OFF TRACK. 70 is unlikely. Focus on learning:
   What's the bottleneck? Fix it. A strong campaign that reaches 
   45–50 customers with a healthy repeat rate is more valuable than 
   burning budget to chase an unachievable number.

WEEK 8 GATE (End of Campaign):
├─ ≥ 70 new customers → MISSION ACCOMPLISHED. 
│   Post-campaign analysis: repeat rate, segment breakdown, 
│   which tier sold most, best-performing channel, creator ROI.
└─ < 70 new customers → Analyse gap:
    - Was the shortfall in paid, organic, seeding, or community?
    - Did any KPI tier achieve its target? If creative KPIs were 
      met but marketing KPIs weren't, the problem was the 
      offer/page. If creative KPIs weren't met, the problem was 
      the message.
    - 50+ customers at ≤ SGD 14 CAC = strong foundation for 
      Campaign #2.
```

---

## 6. Channel-Specific Optimization Plays

### 6.1 Meta Ads — Weekly Optimization Routine

| Action | When | Why |
|--------|------|-----|
| **Check CTR by placement** | Weekly | Reels may outperform Feed. Shift budget to best-performing placement. |
| **Check CPM trend** | Weekly | Rising CPM may indicate audience fatigue. Refresh creative or expand targeting before CPM kills CPA. |
| **Check frequency** | Weekly | If frequency > 3.0 on any ad set, the same people are seeing the ad repeatedly. Expand audience or refresh creative. |
| **Kill underperforming variants** | End of Week 2 | If one video variant's CPA is ≥ 30% higher than the other, pause the loser. Put all budget behind the winner. |
| **Introduce carousel** | Start of Week 3 | Add as a second ad in the winning ad set. The carousel tells the tier story in a different format — some users who skip video will swipe through cards. |
| **Refresh primary text** | Week 5 | If CTR is declining week-over-week, test revised primary text before blaming the creative. Sometimes the words, not the visuals, have fatigued. |

### 6.2 Instagram Organic — Growth Tactics

| Tactic | How | Expected Impact |
|--------|-----|-----------------|
| **Engage in coffee conversations** | 10 min/day: comment genuinely on Singapore coffee posts, home-brewing content, and specialty coffee hashtags. Do not promote. Just be present. | 5–10 profile visits/day. Some become followers. Signals that Coast Coffee is part of the community, not just advertising to it. |
| **Story interactives** | Use polls, quizzes, and question stickers tied to the tier system and brew preferences. Examples: preference-based polls ("Which tier are you?"), origin-guessing quizzes, brew-method questions. These double as informal segment research. | Stories with interactives get higher reach. Polls provide segment data (which tier has the most interest). |
| **Reshare UGC immediately** | When a creator or customer posts about Coast Coffee, reshare to Stories within 24 hours. Tag them. Thank them genuinely. | Encourages more UGC. Shows social proof to profile visitors. |
| **Hashtag strategy** | Use 5–8 targeted hashtags per post, not 30. Mix: Singapore-specific (#specialtycoffeesg #homebaristasg #sgcoffee) + campaign-specific (#asiancoffee #coffeetier) + 2–3 post-specific. Avoid generic #coffee #coffeelover (drowning in noise). | Discoverability without looking spammy. Singapore-specific hashtags have smaller pools but higher intent. |
| **DM early customers** | After a purchase, send a brief personal DM. Thank them for the purchase, express genuine curiosity about which tier they preferred. No secondary ask — relationship-building only. | Builds relationships. Responses = early customer insight. Some will post about the brand unprompted. |

### 6.3 Influencer Content — Amplification

| Scenario | Action |
|----------|--------|
| **Creator post performs well (engagement ≥ 5%, positive comments)** | Ask creator for permission to reshare to Coast Coffee's feed (not just Stories). Credit them. Boost with SGD 20–40 from reserve to a 1% Lookalike of their engaged audience (if possible) or to the broad interest ad set. |
| **Creator post underperforms (engagement < 2%)** | Do not reshare. The content didn't resonate; no loss. The product cost was the only investment. |
| **Creator doesn't post by Week 3** | Send one polite follow-up: "Hey, just checking if the trio arrived okay!" No pressure. If still no post by Week 4, write it off. 3 out of 4 creators posting is still a win. |
| **Creator posts are uniformly positive and mention freshness** | This is the best-case outcome — the vacuum seal and freshness guarantee are visually distinctive enough that creators mention them organically. Compile into a "See what people are saying" carousel or Highlight. |

---

## 7. Risk Mitigation Plays

These are operational responses to the risks identified in the Campaign Strategy §7.

| Risk | Performance Mitigation |
|------|----------------------|
| **Trio economics don't work** | If trio price must rise above SGD 54 or trio is unviable, shift to single-bag offer. Replace the landing page CTA with a 2-question tier quiz ("Safe or adventurous?") → recommend a tier → SGD 5 off first bag. This preserves the curation-led entry. Impact: AOV drops to SGD 13–25 (after discount), CAC economics tighten. 70 customers becomes harder but not impossible — the quiz adds a lead-capture mechanism for email retargeting. |
| **Meta Pixel not firing** | Stop all spend. Redirect Week 1–2 allocation to organic + seeding only. Launch paid only when Pixel is confirmed. Budget reallocated: extra SGD 200 into creator seeding (2 more creators) and boosted posts from the best-performing organic content. |
| **Creative hook rate < 20%** | By Week 1, if both video variant hook rates are below 20%, brief a revised hook immediately drawing from alternative positioning angles. The Creative Brief §3.4 maps the hook variant framework — any untested angle (freshness/curation/origin) becomes the next test. Run the revised variant with SGD 10/day for 4 days against the better-performing original. If the revised hook outperforms, replace the original. If neither clears 20% by end of Week 2, the stop-loss in §3.3 activates — the creative is not viable for paid distribution at this budget. Shift budget to seeding. |
| **Landing page CVR < 2%** | See §5.2 decision tree. Additionally: consider adding a "Freshness Guarantee" badge row near the Add to Cart button. If trust is the blocker, moving the proof closer to the conversion point can lift CVR 0.5–1%. |
| **Influencer seeding yields no content** | By Week 4, if fewer than 2 creators have posted, activate the fallback: use the SGD 80 reserve to run the carousel ad with a customer-proof angle. If even 2–3 early customers have left reviews or sent DMs, quote them (with permission) in ad copy. |
| **Still at < 50 customers by Week 6** | Accept that 70 is unlikely. Shift objective to quality over quantity: focus on the best-converting audience segment, maximise AOV, and ensure a positive first-purchase experience for every customer who does convert. A small, happy cohort that reorders is more valuable than 70 one-time buyers. Use remaining budget to retarget existing customers with a reorder prompt (tier they didn't buy yet). |

---

## 8. Dependencies & Pre-Flight Checklist

### 8.1 Must Be True Before Any Spend

| # | Dependency | Status | If Not True |
|---|-----------|--------|-------------|
| 1 | Meta Pixel installed and firing Purchase events | ⚠ NEEDS CONFIRMATION | Stop. Do not spend. |
| 2 | Landing page live (trio offer, mobile-optimised, checkout functional) | ⚠ NEEDS CONFIRMATION | Stop. Do not spend. |
| 3 | Hero video assets (2 variants) produced and uploaded to Meta | ⚠ PENDING (see Creative Brief §6.1, A1/A2) | Cannot launch. Chase production. |
| 4 | Trio offer price confirmed (SGD 50–54 validated against COGS) | ⚠ NEEDS CONFIRMATION | Launch with provisional ~SGD 50; adjust all CTAs if confirmed price differs. |
| 5 | Instagram account populated with 6–9 posts pre-launch | ⚠ PENDING (see Creative Brief §5.2 for content calendar) | Can launch ads without this, but profile visitors will see an empty account — trust signal lost. Minimum: 6 posts. |
| 6 | Influencer shortlist identified and DM'd | ⚠ NEEDS ACTION | Delay seeding; organic social proof delayed to Week 4+. |

### 8.2 Should Be True For Optimal Performance

| # | Dependency | Impact If Missing |
|---|-----------|-------------------|
| 7 | Brand voice confirmed by customer | Creative can run with provisional voice (Creative Brief §9); risk of tone mismatch is low because the voice is derived from DNA + research. |
| 8 | PayNow + credit card payment options on landing page | Without PayNow, lose a meaningful portion of Singapore checkout conversions. |
| 9 | GST included in displayed pricing (or clearly noted) | Avoids checkout surprise that kills CVR. |
| 10 | 4 creator confirmations for seeding | 3 is sufficient. 2 is light but workable. |

---

## 9. Summary: The Performance Plan in One Page

```
OBJECTIVE: 70 new customers in 8 weeks | SGD 1,000 budget | CAC ≤ SGD 14

CHANNELS:
  Meta Ads (SGD 800) → 35–45 customers → CPA target ≤ SGD 25
  Instagram Organic     → 10–15 customers → profile as trust layer
  Influencer Seeding    → 10–15 customers → 4 creators × SGD 30 product cost
  Community / WOM       → 5–10 customers  → presence + engagement

WHAT SUCCESS LOOKS LIKE (the numbers that matter):
  Business:  70 customers | CAC ≤ SGD 14 | AOV ≥ SGD 50
  Marketing: CVR ≥ 3% | CPA ≤ SGD 25 | CTR ≥ 1.0%
  Creative:  Hook rate ≥ 25% | Engagement ≥ 4% | Completion ≥ 30%

THE FIRST 2 WEEKS ARE EVERYTHING:
  - Launch both hook variants simultaneously
  - If CTR < 0.8% by end of Week 2 → fix the creative hook
  - If CVR < 2% by end of Week 2 → fix the landing page
  - If Pixel isn't firing → fix it before spending another dollar
  - STOP-LOSS: If < 5 purchases or CPA > SGD 50 after SGD 200 spent,
    pause Meta; redirect SGD 600 to seeding + organic amplification

THE MID-POINT CHECK (Week 4):
  - ≥ 30 customers → on track
  - < 20 customers → re-forecast; 70 is unlikely; focus on learning

IF IT WORKS: Scale the winner. Retarget. Introduce carousel. 
IF IT DOESN'T: Fix the bottleneck. Don't burn budget. The stop-loss 
protects SGD 600 from being wasted on underperforming paid channels.
```

---

*End of performance plan. Every channel choice, KPI target, budget figure, and optimization trigger is grounded in the Customer DNA, Campaign Strategy, Campaign Goal, Brand Strategy, and Market Research. Creative copy, content calendar specifics, and asset-level creative direction live in the Creative Brief (`campaigns/coast-coffee-test-three/creative-brief.md`). The performance plan specifies what formats run where, at what budget, measured against which KPIs, with which decision rules — and nothing more. Ready for execution.*

# Performance Plan — Coast Coffee Launch

> **Date:** 2025-07-16  
> **Grounded in:** Customer DNA (`customers/coast-coffee/dna.md`), Campaign Goal (`campaigns/coast-coffee-test-three/goal.md`), Campaign Strategy (`campaigns/coast-coffee-test-three/campaign-strategy.md`), Creative Brief (`campaigns/coast-coffee-test-three/creative-brief.md`), Asset Prompts (`campaigns/coast-coffee-test-three/asset-prompts.md`), Market Research (`campaigns/coast-coffee-test-three/research.md`)  
> **Agent:** Performance Marketing Agent  
> **Status:** Complete — ready for campaign execution

---

## 0. Performance Plan Summary

This plan operationalises the Campaign Strategy for execution. It details channel setup, campaign architecture, audience targeting, bid strategy, tracking requirements, and optimization decision rules — all calibrated to the single objective: **acquire 70 new customers in 8 weeks on SGD 1,000 total paid spend.**

**The core performance logic (from Campaign Strategy §0):** Paid budget alone cannot reach 70 customers. Meta Ads (SGD 800) are expected to deliver 35–40 customers at a CPA of SGD 22–25. Google Search (SGD 150) captures 3–5 customers from intent-driven queries. Organic and community content must deliver the remaining 25–30 customers at zero media cost. The performance plan below governs the paid portion — making every dollar traceable to a customer.

---

## 1. Channel Selection & Rationale

### 1.1 Channels Selected

| Channel | Role | Budget (SGD) | Expected Customers | Primary KPI |
|---------|------|-------------|---------------------|-------------|
| **Meta Ads (IG + FB)** | Primary paid acquisition — prospecting + retargeting | 800 (80%) | 35–40 | Cost per purchase ≤ SGD 25 |
| **Google Search** | Defensive brand capture + long-tail intent | 150 (15%) | 3–5 | Cost per purchase ≤ SGD 25 |
| **Reserve / Testing** | Creative iteration, unforeseen opportunities | 50 (5%) | — | — |
| **Total Paid** | | **1,000** | **~40–45** | Blended CPA ≤ SGD 25 |

**Note:** Organic and community channels (Instagram, TikTok, Reddit, FB coffee groups) are expected to contribute 25–30 additional customers at zero media cost, bringing the total to 70. Those channels are outside this performance plan's scope — they are managed by the founder (see Campaign Strategy §10.3).

### 1.2 Why Meta Dominates (80% of Budget)

**Grounded in DNA constraints (small budget, Singapore-local, home barista audience) and Research findings:**

| Factor | Why It Favours Meta | Grounding |
|--------|--------------------|-----------|
| **Interest targeting granularity** | Meta allows targeting by coffee-specific interests (specialty coffee, pour-over, V60, Aeropress, Hario, Fellow, single-origin coffee, coffee subscription). No other platform offers this precision at this budget. | DNA: target is Singapore home baristas. Research §5: four sub-segments defined by brewing behaviour. Meta's interest taxonomy maps directly to these. |
| **Visual format suitability** | Coffee is inherently visual — beans, pours, landscapes, vacuum-sealing process. Meta's Reels, Stories, and Feed formats are optimised for this content type. | Creative Brief §0.1: freshness process and Asian origin visuals are the creative signatures. Asset Prompts: 22 assets designed for Meta-native formats. |
| **Singapore user density** | Instagram has strong adoption among the 22–45 demographic in Singapore and is widely referenced as a discovery platform for F&B brands in the market. Facebook reaches the 30–45 range well. *(Assumption based on general knowledge of Singapore's digital landscape; validate with platform audience planner during setup.)* | DNA: Singapore is the exclusive market. Research §3.2 identifies high smartphone penetration and notes Instagram as a discovery platform. |
| **Lower CPM** | Meta CPM for food/beverage interest audiences in Singapore is generally lower than TikTok Ads or YouTube for comparable targeting. *(Exact CPM range to be confirmed during campaign setup — the SGD 12 CPM target in §2.2 is the planning assumption.)* | Campaign Strategy §1.2: Meta offers the best CPM among visual platforms for interest-targeted audiences in Singapore. |
| **Retargeting capability** | Meta Pixel + Custom Audiences enable retargeting website visitors, video viewers, and IG profile visitors — critical when 97% of first-time visitors won't convert. | Campaign Strategy §1.1: retargeting is a core design principle. The trust barrier (DNA: inferred HIGH severity — "Can I trust a new, small brand?") means multiple exposures are needed. |

### 1.3 Why Google Search Is Small and Defensive (15%)

**Grounded in the new-brand reality (DNA: no existing search volume for "Coast Coffee"):**

- **No brand search volume at launch.** Bidding on "Coast Coffee" costs near-zero but also gets near-zero impressions until organic/community activity drives searches. The campaign exists to capture those searches when they happen, not to generate them.
- **Long-tail intent terms** ("Asian coffee beans Singapore," "Yunnan coffee Singapore," "buy specialty coffee online Singapore") have low volume but high intent. CPC on these terms is typically SGD 0.50–1.50 — efficient at this budget. *(Assumption — actual CPC to be confirmed during keyword planner research in Google Ads setup.)* These searchers are further down the funnel than social media browsers.
- **Why not more budget:** Generic terms like "specialty coffee Singapore" or "buy coffee beans Singapore" have CPCs of SGD 2–5+ and are dominated by established roasters with higher budgets and Quality Scores. At SGD 150 total, every click must come from a high-intent query — not a browse-level search.

### 1.4 Channels Explicitly Not Selected (and Why)

| Channel | Reason for Rejection | Grounding |
|---------|---------------------|-----------|
| **TikTok Ads (paid)** | CPM competitive but repurposed IG Reels underperform on TikTok's paid algorithm. Organic TikTok is zero-cost upside. | Campaign Strategy §1.2. Budget too small to support platform-native creative for two platforms. |
| **Influencer (paid)** | Even micro-influencers at SGD 50–100/post consume budget better spent on Meta's measurable reach. Deferred to Campaign #2. | DNA: no existing social proof. Paid influencer at this stage is inefficient — the brand needs baseline customers first. |
| **Google Display / YouTube** | CPM higher than Meta for comparable targeting; display CTRs are significantly lower. | Budget constraint: SGD 125/week cannot sustain a reach campaign on multiple networks. |
| **Email marketing** | No list exists. First 70 customers become the seed list. | DNA: brand is new. Campaign Strategy §1.2: "Not applicable yet." |

---

## 2. KPI Plan — All Three Tiers

### 2.1 Business KPI

| Metric | Target | Why This Number (Math + Grounding) |
|--------|--------|-----------------------------------|
| **New customers (8 weeks)** | 70 | Primary objective from goal.md. |
| **Blended CAC** | ≤ SGD 14 | SGD 1,000 ÷ 70 = SGD 14.29. Paid-only CAC will be higher (~SGD 22–25 for the ~40 paid customers). Organic must deliver 25–30 customers at SGD 0 media cost to hit the blended figure. |
| **AOV** | Scenario A (trio margin viable): ≥ SGD 50 | Driven by trio offer at SGD 50–54. Requires trio share ≥75% of orders and single-bag orders averaging SGD 28+. Math: 75% × SGD 52 + 25% × SGD 28 = SGD 46. At 80% trio share with SGD 52 AOV and SGD 28 single-bag: 80% × SGD 52 + 20% × SGD 28 = SGD 47.20. To clear SGD 50, trio share must be ≥80% or single-bag orders must reach SGD 30. At 85% × SGD 52 + 15% × SGD 30 = SGD 48.70 → rounded: target ≥85% trio share to confidently clear SGD 50 AOV. |
| **AOV** | Scenario B (trio margin not viable): ≥ SGD 35 | If COGS makes the trio unsustainable at SGD 50–54, the landing page shifts emphasis to single-bag purchases with tier-recommendation framing. AOV drops but margin per bag is protected. The 70-customer target remains; total revenue decreases. |
| **Revenue (8 weeks)** | Scenario A: ≥ SGD 3,500 / Scenario B: ≥ SGD 2,450 | 70 customers × AOV. Against SGD 1,000 spend = 3.5× ROAS (Scenario A) or 2.45× ROAS (Scenario B). |

**Which scenario applies?** The trio offer economics must be confirmed pre-launch (see §10.2 dependency #2). Scenario A is the plan — Scenario B is the fallback. The performance plan is built for Scenario A; if Scenario B is triggered, the AOV and revenue targets shift but the 70-customer count and all other KPIs remain unchanged.

**DNA ground:** The SGD 18–30/bag price band and the trio offer are the only products. The trio is the conversion vehicle (Campaign Strategy §1.1). Its economics must be resolved before launch — the plan cannot be executed against both scenarios simultaneously.

### 2.2 Marketing KPI (Paid Channels)

| Metric | Target | Why This Number (Math + Grounding) |
|--------|--------|-----------------------------------|
| **Landing page conversion rate (CVR)** | ≥ 3.0% | Industry benchmark for DTC food/beverage first-purchase landing pages *(source: general DTC ecommerce benchmarks — the 3% figure is a planning target; actual CVR will be measured from Week 1 and the target may be adjusted based on real data)*. At 3% CVR, achieving 40 paid customers requires ~1,333 landing page visits. At an estimated blended CPC of SGD 0.60–0.75 (Meta + Google), SGD 950 buys ~1,267–1,583 clicks — tight but feasible. |
| **Cost per purchase — Meta** | ≤ SGD 25 | At SGD 25 CPA, SGD 800 in Meta spend delivers 32 customers. If CPA drifts above SGD 30, paid contribution drops below 27 — making the 70-goal unattainable given organic's realistic ceiling. |
| **Cost per purchase — Google Search** | ≤ SGD 25 | At SGD 25 CPA, SGD 150 delivers 6 customers. Long-tail intent queries typically convert at higher rates than social traffic, so CPA should be lower — a realistic target is SGD 15–20. |
| **CTR — Meta prospecting** | ≥ 1.0% | Planning benchmark for Singapore interest-targeted food/beverage campaigns *(assumption — actual CTR will be measured Week 1; this is the threshold for scaling, not a guarantee)*. Below 1.0% signals creative/messaging isn't resonating — early warning to iterate before scaling. |
| **CTR — Meta retargeting** | ≥ 2.0% | Retargeting audiences are warmer — higher CTR is expected. Below 2.0% suggests the retargeting creative isn't differentiated enough from prospecting (viewers are seeing the same message twice). |
| **CPC — Meta prospecting** | ≤ SGD 0.80 | At this CPC, SGD 500 in prospecting buys 625+ clicks. The estimate is derived from the CPM target (≤ SGD 12) and CTR target (≥ 1.0%): SGD 12 CPM ÷ 10 clicks per 1,000 impressions = SGD 1.20 CPC at 1.0% CTR. To reach SGD 0.80 at SGD 12 CPM, CTR needs to be ≥ 1.5%. This means either CPM must be lower or CTR higher than the floor — both achievable with strong creative. *(To be validated with real Week 1–2 data.)* |
| **CPM — Meta** | ≤ SGD 12 | Planning target for Singapore Meta food/beverage interest audiences *(assumption — verify during campaign setup; if actual CPM is materially higher, adjust CPC and CPA expectations accordingly)*. Higher CPM erodes reach and raises CPC. If CPM exceeds SGD 15 by Week 2, audience targeting or creative needs adjustment. |
| **Frequency — Meta prospecting (weekly)** | 2.0–3.5 | Below 2.0: under-exposed; above 3.5: risk of ad fatigue in a small Singapore audience. Monitor weekly. |
| **Google Search CTR** | ≥ 3.0% | For exact/phrase match on relevant long-tail terms. Below 3.0% suggests ad copy isn't matching search intent. |

### 2.3 Creative KPI

| Metric | Target | Why This Number (Grounding) |
|--------|--------|---------------------------|
| **Hook rate (3-second / thumb-stop) — paid video** | ≥ 25% | On Meta, the first 3 seconds determine whether someone watches or scrolls. The freshness vacuum-seal moment and Asian origin landscapes are inherently scroll-stopping (Creative Brief §0.1). Below 25% means the hook isn't working — kill the variant and test a new hook concept. *(Planning target — the Campaign Strategy §4.4 identifies this as the top of the KPI chain. Validate against Week 1 data.)* |
| **Video completion rate — 15s+ content (ThruPlay)** | ≥ 30% | For longer-form content (Theme B: 18–20s origin story). Signals content quality and audience interest depth. Meta optimises for ThruPlay by default — campaigns should use this objective. |
| **Engagement rate — organic IG** | ≥ 4% | Singapore food/beverage organic engagement benchmark *(assumption — validate against the brand's own organic post performance after Week 2)*. The home barista community is passionate — process content and origin stories invite comments, saves, and shares. |
| **CTR — paid static (trio product images)** | ≥ 0.8% | Static images typically have lower CTR than video. Below 0.8% suggests the product shot isn't compelling enough — test lifestyle vs. flat-lay vs. bag-only approaches (Asset Prompts §5a–5c). |
| **Carousel CTR — Tier Match** | ≥ 1.5% | Carousels invite swipe interaction — CTR benchmark is higher than static. The tier-by-tier reveal structure (Asset Prompts §6) is designed to earn swipes. |

### 2.4 KPI Interdependence — The Decision Chain

These KPIs form a chain. The Campaign Strategy (§4.4) stated the rule: **fix the earliest broken metric first.**

```
Hook rate ≥ 25%
    ↓
CTR ≥ 1.0% (prospecting)
    ↓
CPC ≤ SGD 0.80
    ↓
Landing page visits → sufficient volume
    ↓
CVR ≥ 3.0%
    ↓
CPA ≤ SGD 25
    ↓
Blended CAC ≤ SGD 14
    ↓
70 new customers
```

**Diagnostic rules (apply during weekly optimisation):**

| Symptom | Most Likely Cause | Fix |
|---------|------------------|-----|
| Hook rate < 25%, CTR normal | Hook is weak but those who stay click through | Replace hook shot/first 3 seconds. The creative is good but the opening isn't earning attention. |
| Hook rate ≥ 25%, CTR < 1.0% | Creative holds attention but doesn't motivate action | Examine the CTA, the offer clarity, or the end card. The creative is watchable but not persuasive. |
| CTR ≥ 1.0%, CPC > SGD 0.80 | Audience competition or relevance issue | Narrow audience interests. Check relevance score / quality ranking. If CPM is the cause (>SGD 15), test a different interest cluster. |
| CVR < 2.5% despite healthy traffic | Landing page problem — not the ads | Check: page load speed (especially mobile), trio offer prominence, freshness guarantee visibility, purchase flow friction. The ads are doing their job; the page isn't. |
| CPA > SGD 25 despite healthy CTR + CVR | CPC too high or CVR not high enough to compensate | If CPC is the cause → adjust audience/bidding. If CVR is the cause → landing page optimisation. |
| Retargeting CPA same or higher than prospecting CPA | Retargeting audience too small or creative identical to prospecting | Wait for audience to grow (need ≥1,000 users per audience). Differentiate retargeting creative — use objection-handling messaging ("Still deciding? Here's why our freshness is different."). |

---

## 3. Budget Allocation — Detailed

### 3.1 Line Items

| Line Item | Amount (SGD) | % of Budget | Weekly Run Rate | Start Week |
|-----------|-------------|-------------|-----------------|------------|
| **Meta — Prospecting** | 500 | 50% | ~SGD 83 (Wk 1–6) | Week 1 |
| **Meta — Retargeting** | 250 | 25% | ~SGD 42 (Wk 3–8) | Week 3 |
| **Google Search** | 150 | 15% | ~SGD 25 (Wk 3–8) | Week 3 |
| **Reserve / Testing** | 50 | 5% | As needed | Any |
| **TOTAL PAID** | **1,000** | **100%** | **~SGD 125/week** | |

### 3.2 Week-by-Week Spend Phasing

| Phase | Weeks | Weekly Paid Spend | Meta Prospecting | Meta Retargeting | Google Search | Reserve Draw | Focus |
|-------|-------|-------------------|-----------------|------------------|---------------|-------------|-------|
| **Setup + Test** | 1 | SGD 75 | SGD 75 | — | — | — | Launch 3–5 ad variants. Find the winner. |
| | 2 | SGD 100 | SGD 100 | — | — | — | Kill underperformers. Scale winner(s). |
| **Scale** | 3 | SGD 125 | SGD 75 | SGD 25 | SGD 25 | — | Full funnel live. Retargeting + Search on. |
| | 4 | SGD 130 | SGD 80 | SGD 25 | SGD 25 | — | Mid-campaign review. Course-correct if needed. |
| | 5 | SGD 130 | SGD 75 | SGD 30 | SGD 25 | — | Optimise toward best audiences/creative. |
| | 6 | SGD 130 | SGD 70 | SGD 35 | SGD 25 | — | Shift toward retargeting as pool grows. |
| **Close** | 7 | SGD 110 | SGD 40 | SGD 45 | SGD 25 | — | Retargeting-heavy. Harvest momentum. |
| | 8 | SGD 75 | SGD 20 | SGD 35 | SGD 20 | — | Final retargeting push. Close. |
| **Reserve** | Any | — | — | — | — | SGD 50 | Deploy where it closes the gap to 70. |
| **TOTAL** | **8 wks** | **SGD 1,000** | **SGD 500** | **SGD 250** | **SGD 150** | **SGD 50** | |

### 3.3 The Phasing Rationale (Grounded in DNA + Strategy)

- **Weeks 1–2 at reduced spend (SGD 75–100):** Coast Coffee has zero performance data (DNA: baseline metrics are `<TO CONFIRM>` — no existing traffic or conversion data). Spending the full SGD 125/week on untested creative is wasteful. Reduced spend buys enough data (~500–700 impressions per variant) to identify a winner while preserving budget for scaling. The Brand Strategy (§6) notes brand voice is unconfirmed — Week 1 testing doubles as voice validation: the variant that wins on data tells you which tone resonates.
- **Weeks 3–6 at full spend (SGD 125–130):** The core acquisition phase. Winning creative is scaled. Retargeting audiences are populated (need ≥1,000 users per audience for efficient delivery — achieved after 2 weeks of prospecting). Google Search captures intent signals generated by organic/community activity. The slight overspend in these weeks (SGD 130 vs. 125) is funded by the Weeks 1–2 underspend.
- **Weeks 7–8 at reduced spend (SGD 110 → 75):** Retargeting pool is at its largest and most efficient. New prospecting winds down — the remaining reach is better spent on warm audiences closer to conversion. Reserve deployed where it can close the gap to 70.

### 3.4 Budget Guardrails

- **Do not front-load.** The largest weekly spend (SGD 130) occurs in Weeks 4–6 — after creative winners are identified. Spending aggressively before data exists risks the entire budget.
- **Meta daily budget vs. lifetime budget.** Use daily budgets, not lifetime — they allow faster adjustment. Set each ad set's daily budget to the weekly target ÷ 7.
- **Google Search daily budget.** Set to SGD 3.50/day (SGD 25/week ÷ 7). Google may overserve on some days — the monthly budget cap prevents overspend.
- **Reserve release rule.** Reserve is only deployed if: (a) a clear opportunity exists (e.g., a creative variant with CPA SGD 15 — scale it), or (b) the campaign is at 60+ customers entering Week 8 and the reserve can close the gap.

---

## 4. Meta Ads Campaign Architecture

### 4.1 Campaign Structure

```
META ADS ACCOUNT
│
├── CAMPAIGN 1: CC-Prospecting (Objective: Sales / Conversions)
│   ├── Ad Set 1.1: Interest — Specialty Coffee Core
│   │   └── Ads: Load 3–5 video ad variants from the Creative Brief's three themes
│   │       (Theme A — Freshness Process, Theme B — Asian Origin, Theme C — Tier Match),
│   │       including tonal variants. See §4.4 for loading strategy.
│   │
│   └── Ad Set 1.2: Interest — Home Brewing Methods (launch Week 2 if budget allows split)
│       └── Ads: Load remaining untested variants from the Creative Brief's theme/variant matrix.
│
├── CAMPAIGN 2: CC-Retargeting (Objective: Sales / Conversions) [Launch Week 3]
│   ├── Ad Set 2.1: Website Visitors — 30-day window
│   │   └── Ads: Trio product statics, Theme C carousel, Theme A square cutdown
│   │
│   ├── Ad Set 2.2: Video Viewers — ≥50% watch, 30-day window
│   │   └── Ads: Theme C and Theme B square cutdowns
│   │
│   └── Ad Set 2.3: IG Profile Visitors — 30-day window
│       └── Ads: Trio product static (bag-only), Theme C carousel
│
└── CAMPAIGN 3: CC-Organic-Boost (Objective: Engagement / Video Views) [Optional, reserve-funded]
    └── Boost top-performing organic post (founder-directed, small budget)
```

### 4.2 Prospecting — Detailed Targeting

**Ad Set 1.1 — Specialty Coffee Core (primary)**

| Parameter | Setting | Rationale |
|-----------|---------|-----------|
| **Location** | Singapore (living in or recently in) | DNA: Singapore-local only. |
| **Age** | 22–45 | Home baristas with disposable income for SGD 18–30 specialty beans. Younger than 22: likely student budget. Older than 45: lower Instagram penetration for this interest category. |
| **Gender** | All | Coffee brewing is not gender-skewed in Singapore's specialty scene. |
| **Languages** | English (All) | DNA: English is the confirmed primary language. |
| **Detailed targeting — Interests** | Specialty coffee, Single-origin coffee, Coffee preparation, Homebrewing (coffee), Pour-over coffee, Coffee roasting | These interests map to the four audience segments (Research §5). "Specialty coffee" catches broad interest (Safe Brewers, Convenience Seekers). "Pour-over coffee" and "Coffee preparation" catch deeper engagement (Flavour Explorers, Identity Brewers). |
| **Detailed targeting — Behaviours** | Engaged Shoppers | Optional overlay — targets users who have clicked a CTA on an ad in the past 7 days. May reduce audience size but increase conversion intent. Test with and without. |
| **Exclusions** | Purchasers (once pixel tracks purchases) | Prevent showing prospecting ads to existing customers. Not applicable at launch (zero customers) — add exclusion once the first purchases fire. |
| **Placements** | IG Feed, IG Stories, IG Reels, FB Feed, FB Stories, FB Reels, FB Video Feeds, Audience Network (off — exclude) | The creative assets are designed for these formats (Asset Prompts: 9:16, 1:1, 16:9). Audience Network excluded — low-quality placements, poor CVR, budget waste. |
| **Estimated audience size** | To be confirmed during campaign setup in Meta Ads Manager. *(Planning estimate based on Singapore specialty coffee interest categories: likely in the mid-to-high hundreds of thousands. This will be verified in the platform's audience estimation tool before launch. Sufficient for 8-week campaign without saturation at this budget.)* | |
| **Optimisation goal** | Conversions → Purchase | The campaign objective is acquiring customers, not generating traffic. Meta's algorithm optimises for the event you tell it to. |
| **Conversion window** | 7-day click, 1-day view | Standard for a considered purchase (Research §1.3: purchase cycle is not impulse). 7-day click captures the evaluation window. 1-day view captures immediate post-impression conversions. |
| **Bid strategy** | Lowest cost (no bid cap initially) | With a new pixel and no conversion history, bid caps restrict delivery. Start with lowest cost to let Meta's algorithm learn. If CPA stabilises above SGD 25 after 50+ conversions, switch to cost cap at SGD 25. |

**Ad Set 1.2 — Home Brewing Methods (secondary, launch Week 2 if budget allows)**

| Parameter | Setting | Rationale |
|-----------|---------|-----------|
| **Detailed targeting — Interests** | V60, Aeropress, Hario, Fellow Products, Chemex, Kalita, Coffee grinder, Burr grinder, Gooseneck kettle | Targets users who have self-identified by brewing equipment — a strong signal of home barista identity. This is a narrower, higher-intent audience than the broad "specialty coffee" interest group. |
| **Estimated audience size** | To be confirmed during campaign setup. *(Expected to be smaller than Ad Set 1.1 — verify in Meta Ads Manager audience estimation tool before launch.)* | Smaller but higher-intent. At SGD 125/week, this ad set will saturate quickly — launch in Week 2 once Ad Set 1.1 has established baselines. |
| **All other settings** | Same as Ad Set 1.1 | Consistency across prospecting ad sets for clean comparison. |

**Why this two-ad-set structure (not one, not five):**

- **One ad set** is simpler but pools all interests — Meta's algorithm may optimise toward the broadest (cheapest) interests rather than the highest-converting ones.
- **Two ad sets** separates broad coffee interest from deep equipment interest — meaningful difference in audience intent. The budget can shift between them based on performance.
- **Five ad sets** would fragment a SGD 125/week budget — each ad set gets too little spend to exit the learning phase. Meta's learning phase requires ~50 conversion events per ad set per week. At this budget, even one ad set may struggle — two is the maximum.

### 4.3 Retargeting — Detailed Audiences

**All retargeting campaigns launch Week 3.** Rationale: the audience pools need 2 weeks of prospecting traffic to reach minimum viable size (~1,000 users per audience).

| Audience | Source | Window | Expected Size (by Week 3) | Ad Creative Approach | Rationale |
|----------|--------|--------|--------------------------|---------------------|-----------|
| **Website Visitors — All** | Meta Pixel: PageView event on landing page | 30 days | 1,000–1,500 *(estimate — dependent on Week 1–2 click volume)* | Trio product statics, carousel, Theme A square cutdown | Broadest retargeting pool. These users showed enough interest to click — they know Coast Coffee exists. Creative should reinforce the trio offer and freshness guarantee. |
| **Video Viewers — ≥50%** | Meta: video watch percentage ≥50% on any prospecting ad | 30 days | 400–800 *(estimate — dependent on Week 1–2 video engagement)* | Theme C Tier Match, Theme B Origin | These users watched most of a video — highest-intent signal short of a click. They engaged with the content but didn't visit the site. Creative should push toward the landing page — they're already interested; they need the next step. |
| **IG Profile Visitors** | Meta: Instagram business profile visitors | 30 days | 300–600 *(estimate — dependent on Week 1–2 profile traffic)* | Trio product static (bag-only), carousel | These users looked up the brand after seeing an ad or organic post. High intent — they're researching. Creative should be clean product-focused with a soft CTA. |

**Exclusions across retargeting ad sets:** Exclude purchasers (Purchase event, 30-day window) from all retargeting ad sets. Someone who already bought should not see a "discover your tier" retargeting ad — they see post-purchase content instead (organic, email — outside this plan's scope).

### 4.4 Ad Creative Loading — Week 1 Setup

**Loading strategy:** Load 3–5 video ad variants from the Creative Brief's three themes into Ad Set 1.1. The Creative Brief defines nine possible variants (three themes × three tonal approaches each). Week 1 should test a diverse selection spanning all three themes and a range of tonal approaches — enough to identify a winning creative direction, but not so many that the SGD 75/week budget fragments below statistical significance (~500+ impressions per variant).

The Performance Marketing agent selects the specific variants to load based on which combinations of theme and tone provide the widest coverage across the audience segments (Research §5). The Creative Brief's tonal variants (§2.1–§2.3: A1/A2/A3, B1/B2/B3, C1/C2/C3) are the raw material. The selection should include at least one variant from each theme.

**Why not all nine at once:** Three themes × three tonal variants = nine possible ads. Running nine simultaneously on SGD 75/week fragments the budget — each ad gets ~SGD 8/week, insufficient for statistical significance. Five ads give each variant ~SGD 15/week in Week 1 — enough for 500–800 impressions per variant, sufficient to measure hook rate and directional CTR.

**Week 2 action:** The optimization rules in §8.1 govern which variants live and die. Kill any variant below 20% hook rate or 0.8% CTR after 1,000+ impressions. Promote the winner(s). If no variant clears the thresholds, launch the remaining untested variants as replacements.

### 4.5 Meta Ads Technical Setup Checklist

**Before a single dollar is spent, verify:**

- [ ] **Meta Pixel installed** on the landing page. Verify with Meta Pixel Helper browser extension.
- [ ] **Standard events firing correctly:**
  - `PageView` — fires on every landing page load
  - `ViewContent` — fires when a user views the trio product or any product detail
  - `AddToCart` — fires when a user adds the trio (or any bag) to cart
  - `InitiateCheckout` — fires when checkout flow begins
  - `Purchase` — fires on the order confirmation/thank-you page, with `value` parameter (order total in SGD) and `currency` parameter (SGD)
- [ ] **Conversions API (CAPI)** configured if the platform supports it (Shopify: built-in; WooCommerce: plugin; custom: manual integration). CAPI improves event matching and attribution accuracy.
- [ ] **UTM parameters** appended to all ad links (see §6.2 below)
- [ ] **Attribution setting:** 7-day click, 1-day view (default; verify in Ads Manager)
- [ ] **Campaign budget optimisation (CBO):** OFF. Use ad set budgets (ABO) for this campaign — the budget is too small for CBO to optimise effectively across ad sets, and manual control is needed for the phasing strategy in §3.2.
- [ ] **Ad preview:** Verify each ad renders correctly on IG Feed, IG Stories, IG Reels, FB Feed, and FB Stories before activating. Check text safe zones, product visibility, and CTA button placement.

---

## 5. Google Ads Campaign Architecture

### 5.1 Campaign Structure

```
GOOGLE ADS ACCOUNT
│
└── CAMPAIGN: CC-Search (Objective: Sales)
    ├── Ad Group 1: Brand Terms
    │   ├── Keyword: [coast coffee singapore] (exact)
    │   ├── Keyword: [coast coffee] (exact)
    │   ├── Keyword: "coast coffee singapore" (phrase)
    │   └── Keyword: "coast coffee" (phrase)
    │
    ├── Ad Group 2: Long-Tail — Asian Origins
    │   ├── Keyword: [asian coffee beans singapore] (exact)
    │   ├── Keyword: [yunnan coffee singapore] (exact)
    │   ├── Keyword: [thai coffee beans singapore] (exact)
    │   ├── Keyword: [indonesian coffee beans singapore] (exact)
    │   ├── Keyword: "asian specialty coffee singapore" (phrase)
    │   ├── Keyword: "single origin asian coffee" (phrase)
    │   └── Keyword: "asian coffee delivery singapore" (phrase)
    │
    └── Ad Group 3: Long-Tail — Purchase Intent
        ├── Keyword: [buy specialty coffee online singapore] (exact)
        ├── Keyword: [coffee trio singapore] (exact)
        ├── Keyword: [coffee bean delivery singapore] (exact)
        ├── Keyword: "specialty coffee delivery singapore" (phrase)
        ├── Keyword: "buy coffee beans online singapore" (phrase)
        └── Keyword: "single origin coffee delivery singapore" (phrase)
```

### 5.2 Google Ads Settings

| Parameter | Setting | Rationale |
|-----------|---------|-----------|
| **Networks** | Search Network only | Search Partners and Display Network excluded — budget is too small for non-search inventory. |
| **Location** | Singapore (presence or interest) | DNA: Singapore-local only. |
| **Languages** | English | DNA: English is primary. |
| **Bid strategy** | Manual CPC (initially) → Target CPA (after 15+ conversions) | Start with manual CPC (max SGD 2.00/bid) to control costs during the learning period. Once the campaign accumulates 15+ conversions with a stable CPA, switch to Target CPA at SGD 20–25 to let Google's algorithm optimise. |
| **Ad schedule** | All days, 7:00–23:00 SGT | Home baristas browse during waking hours. Overnight searches (midnight–7am) are lower-intent and more likely to be idle browsing — exclude to preserve budget. |
| **Daily budget** | SGD 3.50 (SGD 25/week) | Matches the budget phasing in §3.2. Google may overspend on some days; the monthly budget cap (campaign-level) prevents runaway spend. |
| **Ad rotation** | Rotate evenly (initially, for 30 days) → Optimise for clicks/conversions | Start with even rotation to fairly test ad copy variants. After 30 days or 1,000+ impressions, switch to conversion-optimised rotation. |
| **Conversion tracking** | Google Ads conversion tag or import from platform | The Purchase event must be tracked. If the landing platform supports Google Ads conversion tracking natively, use it. If not, ensure a Google Ads tag fires on the purchase confirmation page. |

### 5.3 Search Ad Copy

Search ad copy will be written during campaign setup based on the Creative Brief's tonal guardrails (§6). This plan covers only the targeting, bidding, and structural setup for Google Ads — not what the ads say.

### 5.4 Google Ads — Negative Keywords

Add as campaign-level negatives to prevent wasted spend:

| Negative Keyword | Reason |
|-----------------|--------|
| "jobs," "career," "hiring" | Not a job search query |
| "wholesale," "bulk," "supplier" | Not a B2B business (yet) |
| "kopi," "kopitiam," "hawker" | Not the product category — traditional Singapore coffee, not specialty |
| "instant," "3-in-1," "nescafe" | Commodity coffee — wrong category |
| "starbucks," "coffee bean" (the chain, not the product) | Chain retail — wrong category |
| "free," "cheap," "budget" | Price-point mismatch — Coast Coffee is SGD 18–30/bag |
| "espresso machine," "coffee machine" | Equipment, not beans |

---

## 6. Tracking & Measurement Setup

### 6.1 Tracking Infrastructure — Non-Negotiable

**The following must be live before Week 1, Day 1 spend. No exceptions.**

| Component | Tool / Method | What It Tracks | Why It's Non-Negotiable |
|-----------|--------------|----------------|------------------------|
| **Meta Pixel** | Meta Pixel base code on all landing pages | PageView, ViewContent, AddToCart, InitiateCheckout, Purchase | Without the pixel, Meta cannot attribute conversions, optimise delivery, or build retargeting audiences. The campaign would be flying blind. |
| **Meta Conversions API (CAPI)** | Server-side event forwarding (Shopify: native; custom: manual) | Same events as pixel, server-side | Improves attribution accuracy when browser pixel is blocked (~10–20% of Safari/Firefox users). Without CAPI, conversion data is incomplete. |
| **Google Ads conversion tag** | Google Ads tag or Google Tag Manager + imported goals | Purchase event | Required for Google Ads to track conversions and optimise bidding. |
| **UTM parameters** | Manual appending to all paid links (see §6.2) | Source, medium, campaign, content (creative variant) | The only way to know which ad/creative/variant drove which purchase. Without UTMs, all paid traffic is undifferentiated in analytics. |
| **Landing page analytics** | Google Analytics (GA4) or platform-native analytics (Shopify, WooCommerce) | Traffic, behaviour flow, conversion rate, AOV, revenue | Required for CVR monitoring and landing page diagnostics. |

### 6.2 UTM Parameter Convention

All paid ad links must follow this convention. Every ad, every variant, every placement.

**Template:**
```
https://coastcoffee.sg/?utm_source=<platform>&utm_medium=<channel-type>&utm_campaign=cc-launch&utm_content=<variant-identifier>
```

| Parameter | Value | Notes |
|-----------|-------|-------|
| `utm_source` | `meta` or `google` | Platform |
| `utm_medium` | `paid-social` (Meta) or `paid-search` (Google) | Channel type |
| `utm_campaign` | `cc-launch` | Campaign identifier |
| `utm_content` | A unique identifier per ad creative variant | Use a consistent naming convention that maps to the creative brief's theme and variant code (e.g., freshness-a1, origin-b3, tier-c2, trio-lifestyle, carousel-tier). Assign codes when assets are loaded into the ad platforms — one code per ad, never duplicated. |

**Google Search UTMs:**
```
utm_source=google&utm_medium=paid-search&utm_campaign=cc-launch&utm_content=<ad-group>
```
Where `utm_content` is `brand`, `asian-origin`, or `purchase-intent`.

### 6.3 Conversion Tracking Verification Checklist

Before launch, verify each of these fires correctly:

- [ ] **Landing page loads** → Meta Pixel `PageView` event fires. Verify in Meta Events Manager (real-time view).
- [ ] **View trio product page** (or scroll to trio section) → `ViewContent` event fires.
- [ ] **Add trio to cart** → `AddToCart` event fires with `value` and `currency`.
- [ ] **Begin checkout** → `InitiateCheckout` event fires.
- [ ] **Complete purchase** → `Purchase` event fires with `value` (order total) and `currency` (SGD). Verify on the thank-you/confirmation page.
- [ ] **Google Ads conversion tag** fires on purchase. Verify in Google Ads → Tools → Conversions.
- [ ] **UTM parameters** appear in landing page analytics (GA4 or platform analytics) for test clicks from each ad.
- [ ] **Duplicate counting:** Ensure the same purchase is not counted twice (e.g., by both Meta Pixel and Google Ads tag firing on the same page, if using cross-platform attribution). This is a data hygiene issue, not a conversion tracking issue — keep both tags but note that total "conversions" across platforms will exceed actual purchases. Use the platform analytics (Shopify/WooCommerce) as the source of truth for total customers.

---

## 7. Campaign Execution Calendar

### 7.1 Pre-Launch (Before Week 1)

| Task | Owner | Deadline | Notes |
|------|-------|----------|-------|
| Install Meta Pixel + verify events | Performance / Developer | T-3 days | Use Meta Pixel Helper to verify each event. |
| Verify Meta Ads audience sizes for Ad Set 1.1 and 1.2 interests in Singapore | Performance | T-3 days | Use Meta Ads Manager audience estimation tool. Compare to planning assumptions in §4.2. |
| Run Google Keyword Planner to confirm CPC estimates for target keywords | Performance | T-3 days | Compare to planning assumptions in §1.3 and §2.2. |
| Configure Google Ads conversion tracking | Performance / Developer | T-3 days | Verify purchase event fires. |
| Set up Meta Ads campaigns (prospecting only) | Performance | T-2 days | Draft mode — do not activate. Load 3–5 ad variants per §4.4. |
| Set up Google Ads campaigns (draft) | Performance | T-2 days | Paused — activate Week 3. |
| Generate UTM-parameterised URLs for all ads | Performance | T-2 days | One URL per ad variant. Use a UTM builder spreadsheet — no manual typing. |
| Verify landing page: mobile load speed, purchase flow, trio offer visibility | Performance / Developer / Founder | T-1 day | Test on an actual mobile device. Check: page load < 3 seconds on 4G, trio offer is above the fold, "Fresh for 6+ weeks" visible, checkout works with PayNow + card. |
| Confirm trio offer economics — determine whether Scenario A or Scenario B applies (§2.1) | Founder | T-1 day | Final go/no-go on SGD 50–54 trio pricing vs. COGS (Brand Strategy §6, assumption #5). |
| Activate campaigns | Performance | Launch day | Start with SGD 75 daily budget on Meta prospecting. Monitor for 2 hours after activation. |

### 7.2 Week-by-Week Execution

| Week | Day | Action | Owner |
|------|-----|--------|-------|
| **1** | Mon | Activate Meta prospecting (3–5 ad variants, SGD 75/day). Verify impressions serving, no delivery errors. | Performance |
| | Wed | First performance check: Are impressions delivering? Are all variants getting roughly equal spend? Any variant with zero delivery? | Performance |
| | Fri | First data check: Hook rate and CTR per variant (note: data will be thin — directional only). | Performance |
| **2** | Mon | Week 1 review: Kill variants per optimization rules in §8.1. Launch replacement variants if no clear winner. Increase daily budget to SGD 100. | Performance |
| | Fri | Check: Is a clear winner emerging? Prepare retargeting and Google Search campaigns for Week 3 activation. | Performance |
| **3** | Mon | Activate retargeting (all 3 audiences) and Google Search. Total weekly spend now SGD 125. | Performance |
| | Fri | First full-funnel review: Are retargeting audiences populated? Is Google Search getting impressions? Is landing page CVR tracking ≥ 2.5%? | Performance |
| **4** | Mon | Mid-campaign review (see §8.3). Course-correct based on data. | Performance + Founder |
| **5** | Mon | Optimise: shift budget to best-performing audiences, creative, and placements. Kill any underperforming retargeting ad sets. | Performance |
| **6** | Mon | Review: are we tracking to 50–55 customers? What's the 70-outlook? | Performance + Founder |
| **7** | Mon | Shift prospecting budget to retargeting (60% retargeting, 40% prospecting). Deploy reserve if close to 70. | Performance |
| **8** | Mon | Retargeting-only for final push. Reduce total spend to SGD 75. | Performance |
| | Fri | Campaign close. Pause all ads. Final performance report. | Performance |

---

## 8. Optimization Decision Rules

### 8.1 Creative Optimization (Weeks 1–2)

These rules govern which ad variants live and die during the testing phase.

| Rule | Action | Rationale |
|------|--------|-----------|
| Hook rate < 20% after 1,000+ impressions | **Kill.** Replace with next untested variant from the Creative Brief's theme/variant matrix. | The hook is the top of the KPI chain (Campaign Strategy §4.4). A weak hook means the creative never gets a chance to persuade — CTR and CVR downstream are irrelevant. |
| Hook rate ≥ 20%, CTR < 0.8% after 1,000+ impressions | **Kill.** The creative holds attention but doesn't motivate action. | The gap between attention and action is likely the CTA, end card, or offer clarity. Fixable but not worth spending budget to diagnose at this scale — replace with a stronger variant. |
| Hook rate ≥ 25%, CTR ≥ 1.0% | **Keep and scale.** This is the winner. | Both attention and action metrics clear the threshold. Increase this variant's share of the prospecting budget. |
| Hook rate ≥ 25%, CTR 0.8–1.0% | **Keep but monitor.** May improve with audience refinement. | The creative earns attention. The CTR gap may be an audience mismatch (showing the right creative to the wrong people) rather than a creative problem. Test against a different interest cluster before killing. |
| No variant clears both thresholds after Week 2 | **Pause and diagnose.** Check: (a) are the right interests targeted? (b) is the CTA clear? (c) are text overlays readable on mobile? | If all variants underperform, the problem is likely not creative-specific — it's audience targeting or a systemic creative issue (e.g., text too small on mobile, CTA unclear). |

### 8.2 Budget Optimization (Weeks 3–8)

| Rule | Action | Rationale |
|------|--------|-----------|
| Meta prospecting CPA > SGD 25 for 2 consecutive weeks | Reduce prospecting budget by 20%. Shift to retargeting (lower CPA expected). | Prospecting is too expensive. The audience may be saturated or creative fatigued. Retargeting's CPA should be lower because the audience is warmer. |
| Meta retargeting CPA > SGD 25 for 2 consecutive weeks | Reduce retargeting budget by 20%. Check: are audiences large enough (>1,000 per ad set)? Is creative differentiated from prospecting? | Retargeting should outperform prospecting on CPA. If it doesn't, either the audience is too small (delivery issues) or the creative isn't giving them a reason to return. |
| Meta prospecting CPA < SGD 20 | Increase prospecting budget by 10–15%. This is a highly efficient channel — scale it. | Below SGD 20 CPA means the paid channel is outperforming the target. Capture the efficiency while it lasts — performance decays as audiences saturate. |
| Google Search CPA > SGD 30 for 2 consecutive weeks | Pause Google Search. Shift budget to Meta retargeting. | At SGD 25/week, Google Search cannot afford a CPA above SGD 30 — that's ~0.8 customers per week, not worth the management overhead. |
| CVR < 2.5% by Week 4 | Pause all budget increases. Diagnose landing page before spending more on traffic. | At CVR < 2.5%, even perfect ad performance cannot hit the customer target. The bottleneck is the landing page, not the ads. Do not scale traffic into a leaky bucket. |

### 8.3 Mid-Campaign Review (Week 4)

**Decision gate (from Campaign Strategy §7):**

| Metric | Target | Action if Below |
|--------|--------|-----------------|
| Total customers | ≥ 35 (halfway to 70) | If below 30: full funnel diagnostic. Is it a traffic problem (CPC/CTR) or a conversion problem (CVR)? Adjust budget accordingly. |
| Blended CPA | ≤ SGD 14 | If above SGD 18: the 70-goal at SGD 1,000 is unlikely. Consider: (a) increasing budget if possible, (b) reducing target, or (c) extending timeline. |
| Meta prospecting CPA | ≤ SGD 25 | If above SGD 30: reduce prospecting, increase retargeting share, push organic harder. |
| Landing page CVR | ≥ 2.5% | If below 2.5%: this is the priority fix. A/B test headline, trio offer placement, freshness guarantee visibility. |

### 8.4 Final Week Decision Rules (Week 8)

| Customer Count (start of Week 8) | Action |
|----------------------------------|--------|
| 60–69 | Deploy full reserve (SGD 50) to retargeting. Push organic: "last chance" content. Ask early customers for referrals. 70 is within reach. |
| 50–59 | Deploy half of reserve. Accept that 70 is unlikely — push for 60+. Document learnings for Campaign #2. |
| <50 | Conserve remaining budget. The campaign has not achieved sufficient momentum. Do not spend reserve chasing an unreachable target — save it for Campaign #2 with improved strategy. |

---

## 9. Weekly Reporting Template

Every week, the following report should be compiled and reviewed. Data sources: Meta Ads Manager, Google Ads, landing page analytics (GA4 or platform-native), and the founder's organic/community tally.

### 9.1 Paid Performance Dashboard

| Metric | Target | Week 1 | Week 2 | Week 3 | Week 4 | Week 5 | Week 6 | Week 7 | Week 8 |
|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|
| **Spend (SGD)** | — | | | | | | | | |
| ↳ Meta Prospecting | — | | | | | | | | |
| ↳ Meta Retargeting | — | | | | | | | | |
| ↳ Google Search | — | | | | | | | | |
| **Impressions** | — | | | | | | | | |
| **CPM (SGD)** | ≤ 12 | | | | | | | | |
| **Clicks** | — | | | | | | | | |
| **CTR (%)** | ≥ 1.0% (prosp.) / ≥ 2.0% (ret.) | | | | | | | | |
| **CPC (SGD)** | ≤ 0.80 (prosp.) | | | | | | | | |
| **Landing page visits** | — | | | | | | | | |
| **Purchases (paid-driven)** | — | | | | | | | | |
| **CVR (%)** | ≥ 3.0% | | | | | | | | |
| **CPA (SGD)** | ≤ 25 | | | | | | | | |
| **Revenue (SGD)** | — | | | | | | | | |
| **ROAS** | ≥ 3.5× | | | | | | | | |

### 9.2 Creative Performance (per variant — add rows as needed)

| Variant | Impressions | Hook Rate (%) | CTR (%) | CPC (SGD) | Purchases | CPA (SGD) | Status |
|---------|------------|---------------|---------|-----------|-----------|-----------|--------|
| *(populate with UTM content codes as ads go live)* | | | | | | | |
| *(add rows for variants tested in later weeks)* | | | | | | | |

### 9.3 Organic & Community Tally

| Channel | Metric | Week 1 | Week 2 | … | Week 8 |
|---------|--------|--------|--------|-----|--------|
| **IG Organic** | Posts published | | | | |
| | Total engagement | | | | |
| | Engagement rate (%) | | | | |
| | Profile visits | | | | |
| | Website clicks (from bio) | | | | |
| | Customers attributed (code/UTM) | | | | |
| **TikTok Organic** | Posts published | | | | |
| | Total views | | | | |
| | Profile visits | | | | |
| **Community** | Posts/comments (Reddit, FB, HWZ) | | | | |
| | Referral traffic | | | | |
| | Customers attributed | | | | |
| **Total Organic Customers** | | | | | |

### 9.4 Cumulative Customer Tracker

| Source | Week 1 | Week 2 | … | Week 8 | Total |
|--------|--------|--------|-----|--------|-------|
| Meta Prospecting | | | | | |
| Meta Retargeting | | | | | |
| Google Search | | | | | |
| Instagram Organic | | | | | |
| TikTok Organic | | | | | |
| Community (Reddit/FB/HWZ) | | | | | |
| Direct / Word of Mouth / Other | | | | | |
| **Cumulative Total** | | | | | **/70** |

---

## 10. Risks, Dependencies & Contingencies

### 10.1 Performance-Specific Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| 1 | **Meta Pixel fires incorrectly** — Purchase event doesn't fire on the thank-you page, or fires twice | Medium | Critical — without accurate purchase data, Meta cannot optimise, CPA cannot be measured, and retargeting exclusions fail | Pre-launch testing (see §6.3). If discovered mid-campaign: pause prospecting, fix the pixel, verify with a test purchase, then resume. Accept the data gap. |
| 2 | **Meta learning phase doesn't exit** — campaign fails to reach 50 purchase events in 7 days, remaining in "learning limited" | High | High — ad delivery is suboptimal, CPA is unstable, budget is wasted on learning | This is expected at this budget — 50 purchases/week on SGD 125/week requires CPA ≤ SGD 17.50, which is ambitious. Mitigation: (a) use a broader conversion event (AddToCart + Purchase) to accumulate signals faster, (b) set a longer conversion window, (c) accept learning-limited status and rely on manual optimisation. |
| 3 | **Singapore audience saturation** — frequency exceeds 3.5 by Week 4–5, causing ad fatigue and rising CPAs | Medium | Medium — CPA rises, budget efficiency drops | The Singapore specialty coffee interest pool will be verified during campaign setup in Meta Ads Manager. At ~SGD 125/week and ~SGD 12 CPM, this buys ~10,000 impressions/week. Monitor frequency weekly. If frequency exceeds 3.5 for 2 consecutive weeks: (a) refresh creative (use tonal variants not yet tested), (b) expand interests, (c) shift budget to retargeting. |
| 4 | **Google Search drives zero conversions** — long-tail keywords have too little volume | High | Low — Google is only 15% of budget and expected to deliver 3–5 customers | If Google Search delivers zero conversions by Week 8: the budget loss is SGD 150 (15% of total). Not campaign-fatal. If by Week 5 there are zero conversions, pause Google Search and redirect the remaining SGD 75 to Meta retargeting. |
| 5 | **iOS privacy restrictions limit retargeting** — Safari users, app-tracked users not reachable via retargeting audiences | Medium | Medium — retargeting pool is smaller than expected, reducing this channel's contribution | This is structural. Singapore iOS share is ~30–40% *(general knowledge estimate — confirm with platform data)*. The Meta CAPI (see §6.1) partially mitigates. If retargeting audiences are significantly below 1,000 after Week 3: broaden the website visitor window from 30 to 60 days, lower the video view threshold from ≥50% to ≥25%, or combine all retargeting audiences into one ad set to pool reach. |
| 6 | **UTM parameters break or aren't appended** — paid traffic is undifferentiated in analytics | Low | Medium — cannot measure creative-level performance | Pre-launch testing (see §6.3). Use a UTM builder spreadsheet to generate all URLs at once and paste them into ad managers — no manual typing. |

### 10.2 Dependencies

These are conditions that must be met before the performance plan can execute as designed. They are dependencies, not status reports.

| # | Dependency | Blocking Condition | Consequence if Unresolved |
|---|-----------|-------------------|--------------------------|
| 1 | **Creative assets loaded into Meta Ads Manager** | At minimum, 3–5 video ad variants from the Creative Brief must exist as rendered, platform-ready files before Week 1 launch. | Campaign cannot launch. A campaign with no creative assets has nothing to serve. |
| 2 | **Trio offer economics confirmed** | COGS for the trio at SGD 50–54 must be confirmed viable or non-viable before launch. This determines whether Scenario A or Scenario B applies (§2.1). | The AOV target is undefined. Scenario A targets SGD 50 AOV; Scenario B targets SGD 35 AOV. The campaign cannot be optimised against both. |
| 3 | **Landing page built and live** | Trio product visible above the fold, freshness guarantee prominent, mobile checkout with PayNow + card. Must be live before Week 1, Day 1. | Campaign cannot launch. The landing page is the conversion mechanism — paid traffic with no destination is wasted budget. |
| 4 | **Founder bandwidth for organic/community** | Campaign Strategy §10.3 requires 3–5 hours/week from the founder. If this cannot be committed, the paid+organic model breaks. | The 70-customer target becomes unrealistic on SGD 1,000. Options: reduce target to 40–45 (paid-only), increase budget, or extend timeline. |
| 5 | **Meta Ads audience size verified** | During campaign setup, verify that the interest combinations in §4.2 produce viable audience sizes in Meta Ads Manager (minimum ~50,000 for Ad Set 1.1). | If audience is much smaller than expected, saturation risk increases. May need to broaden interests or consolidate to a single ad set. |
| 6 | **Google Keyword Planner CPC estimates confirmed** | During campaign setup, verify that long-tail keyword CPCs align with the SGD 0.50–1.50 planning assumption. | If CPCs are materially higher, the Google Search budget may need to be reduced and reallocated to Meta. |

---

## 11. Post-Campaign — What to Measure Beyond Week 8

The campaign's official KPI is 70 new customers in 8 weeks. But the business objective is sustainable growth. Track these metrics for 90 days post-campaign:

| Metric | Why It Matters | How to Track |
|--------|---------------|--------------|
| **Repeat purchase rate (30/60/90 days)** | Are the 70 customers one-time buyers or the start of a customer base? A repeat rate of 20%+ at 30 days signals product-market fit. | Shopify/WooCommerce: cohort analysis by first-purchase date. Tag all campaign-acquired customers with a "cc-launch" cohort label. |
| **Customer lifetime value (LTV) — early signal** | If the blended CAC is SGD 14 and customers reorder at SGD 25 AOV, the unit economics work even if first-purchase margin is thin. | Track average orders per customer and average AOV over 90 days for the campaign cohort. |
| **Organic acquisition rate — post-campaign** | Did the campaign create enough brand presence that organic acquisition continues after paid stops? This is the real test of brand building. | Track weekly new customers by source after Week 8. If organic drops to near-zero, the brand hasn't achieved self-sustaining visibility. |
| **Best-performing origin / tier** | Which tier(s) drive repeat purchases? Which origin(s) get the most reorders? This data shapes Campaign #2's product and creative strategy. | Analyse purchase data by SKU for the campaign cohort. |
| **Channel CPA — lifetime view** | The campaign measured CPA on first purchase. But if Meta-acquired customers have a 30% repeat rate and Google-acquired customers have a 10% repeat rate, the "true" CPA (including LTV) is very different. | Attribute repeat purchases back to the original acquisition channel (using first-touch UTM/cookie data). |

---

*End of Performance Plan. Handoff to campaign execution — Meta Ads Manager setup, Google Ads setup, tracking verification, and Week 1 activation.*

# Performance Plan — Coast Coffee Launch Campaign

> Author: Performance Marketing Agent. Output is a **performance plan only** — channel selection & setup, KPI plan & instrumentation, budget allocation & pacing, and optimization rules. **No** creative, copy, or assets (those are the Creative Director / Asset Prompt stages).
>
> Grounded in and executed within: `customers/coast-coffee/dna.md` (authoritative constraints/geography), `campaigns/coast-coffee/goal.md` (the numbers), `campaigns/coast-coffee/campaign-strategy.md` (the frame: channel split, phasing, week-3 reallocation rule), `campaigns/coast-coffee/research.md` (channel intelligence, keywords, communities), `campaigns/coast-coffee/brand-strategy.md` (offer, objections), `campaigns/coast-coffee/creative-brief.md` (asset/channel match).
>
> **[DNA]** = from Customer DNA · **[GOAL]** = from goal.md · **[STRATEGY]** = from campaign strategy · **[RESEARCH]** = from research · **[CREATIVE]** = from creative brief · **[REC]** = my recommendation to validate · **[ASSUMPTION]** = explicit modelling assumption to confirm.
>
> **Frameworks applied:** `knowledge/performance/` is currently a stub (no project-defined channel benchmarks, KPI targets, or budget model — see "Knowledge gaps"). In its absence I applied three standard, well-established frameworks and name them per section: a **full-funnel channel-role model** (intent capture vs. demand creation vs. earned trust vs. retargeting) for channel selection, a **three-tier KPI cascade** (Business → Marketing → Creative) for instrumentation, and a **unit-economics / CAC-payback model** for budget allocation. SGD benchmarks below are flagged `[ASSUMPTION]` and must be validated against live data — the DNA has no baseline metrics (`<TO CONFIRM>`).

---

## Executive summary

- **The path to 70 customers is not "buy 70 customers."** On SGD 1,000 paid at a realistic blended paid cost-per-purchase of ~SGD 22–25, paid buys roughly **40–45 first-time buyers**. The remaining **~25–30 must come from earned/organic** (editorial roundups, IG, SG coffee communities) and from **retargeting the warm traffic paid generates**. The blended CAC ≤ SGD 14 target is **only achievable because organic carries ~40% of volume at near-zero marginal cost** — this is the load-bearing assumption of the whole plan. [GOAL][STRATEGY]
- **Channel split (final, in SGD):** Google Search **SGD 300 (30%)**, Meta/IG paid **SGD 400 (40%)**, Retargeting + scale reserve **SGD 300 (30%)**, Organic IG + SG community + editorial **SGD 0 paid (effort)**. This nudges the strategy's indicative 35/45/20 toward a **larger held reserve (30%)** because, on a thin budget with no baseline, the highest-leverage move is concentrating un-committed budget behind the proven winner after the week-3 read. The week-1–2 *deployed* split still honours the strategy's intent (Search and Meta both live, Meta heavier). [STRATEGY §3 — I finalise the detail per §6 handoff.]
- **Google Search earns its budget on intent**, not volume: it is the cheapest path to the ready-to-buy buyer (brand defence + non-brand "buy coffee beans online Singapore," "Asian coffee beans," "coffee sampler/gift Singapore"). [RESEARCH] **Meta/IG earns its budget on demand creation + the visual trio/freshness story + retargeting the wary.** [STRATEGY]
- **Three KPI tiers are instrumented before spend:** Business (70 customers, blended CAC ≤ SGD 14, AOV ≥ SGD 50), Marketing (LP CVR ≥ 3%, paid cost-per-purchase ≤ SGD 25, paid-social CTR ≥ 1.0%), Creative (hook rate ≥ 25%, organic engagement ≥ 4%). [GOAL]
- **Statistical-validity caveat up front:** ~SGD 125/week cannot produce statistically significant A/B reads. Decisions in weeks 1–8 are **directional, guardrail-driven, and biased toward not killing a channel prematurely**, not significance-tested. Treat every benchmark as a hypothesis to be replaced by live data. [REC]

---

## 1. Channel plan

*Framework: full-funnel channel-role model. Channels are fixed by the approved strategy (Google Search, Meta/IG paid, organic IG + SG community/editorial, retargeting) [STRATEGY §3] — I finalise objective, targeting, placements, and the budget rationale for each.*

### Channel A — Google Search (intent capture / BOFU)

- **Objective:** Conversions (purchase). Capture demand that already exists — people actively searching to buy/compare specialty beans in SG. [RESEARCH: "search to buy/compare" behaviour confirmed]
- **Why it earns its budget (tied to the goal):** Search is the **lowest-CAC path to a ready buyer** because intent is pre-formed — you pay to be present at the decision, not to manufacture desire. For a 70-customer goal at CAC ≤ SGD 14, every cheap intent-driven purchase pulls the blended average down and offsets the more expensive demand-creation purchases from Meta. [RESEARCH][GOAL]
- **Campaigns / structure:**
  1. **Brand campaign (exact + phrase: "Coast Coffee", "Coast Coffee Singapore").** Cheap defensive capture so competitors/aggregators don't intercept people who heard about Coast via editorial/organic. *Why:* editorial and IG will drive brand searches; you must own them. Tiny budget, high ROAS. [REC]
  2. **Non-brand specialty / Asian-origin campaign.** The acquisition engine. Keyword themes (not exhaustive — mine the search-terms report weekly):
     - *Buy-intent generic:* "buy coffee beans online singapore", "coffee beans delivery singapore", "specialty coffee beans singapore", "order coffee beans singapore".
     - *Asian-origin differentiator:* "asian coffee beans", "thailand coffee beans", "yunnan / china coffee beans", "indonesian coffee beans singapore". [RESEARCH: Asian-origin trend tailwind; DNA #3]
     - *Sampler / gift intent (matches the trio offer):* "coffee sampler singapore", "coffee gift set singapore", "coffee tasting set / trio singapore". [GOAL offer]
     - *Subscription-adjacent (capture comparison shoppers):* "coffee subscription singapore" — bid low, expect higher CPC and lower CVR; monitor closely. [RESEARCH: competitive term]
  3. **Negative keywords (day-one):** "jobs", "cafe near me", "machine", "nespresso", "starbucks", "free", "cheap", "wholesale", "course", "barista training", "k-cup", "instant". *Why:* on a SGD 300 budget, wasted clicks are fatal; protect the premium, non-price positioning by excluding "cheap/free". [DNA: premium, never price-led]
- **Match types & bidding:** Start **phrase + exact** only (broad match burns thin budgets on irrelevant queries). Bid strategy: begin **Maximise Conversions** to gather conversion data; switch to **Target CPA (≤ SGD 25)** once ~15–30 conversions have accrued (Google needs volume before tCPA is stable — likely not until week 3–4, possibly never at this budget, so manual/Max Conversions may run the whole flight). [REC][ASSUMPTION]
- **Placements:** Search network only. **Exclude Search Partners and the Display Network** at launch — they dilute intent and waste budget. [REC]
- **Geo:** Singapore only. [DNA] **Language:** English (ad language English; consider also targeting people in SG whose browser is set to other languages but serve English creative, per DNA English-primary). [DNA]
- **Budget rationale:** SGD 300 (30%). Enough to maintain presence on a focused non-brand set + brand defence for 8 weeks (~SGD 37/week). *Why not more:* non-brand specialty CPCs in SG are competitive (established roasters bid here [RESEARCH]); over-funding search before we know its CVR risks spending the reserve blind. Search is a **scale candidate** for the week-3 reallocation if its cost-per-purchase beats Meta.

### Channel B — Meta / Instagram paid (demand creation + retargeting / TOFU→BOFU)

- **Objective:** Conversions (purchase), optimising to the **Purchase** event (not link clicks or add-to-cart) once pixel data allows; **Add-to-Cart** as the optimisation event only if Purchase volume is too thin for the algorithm to learn. [REC]
- **Why it earns its budget (tied to the goal):** The audience is confirmed IG-led [RESEARCH], and the brand's two conversion levers — the **visual trio** and the **freshness/process proof** — are inherently visual and need to be *shown* to a cold audience that isn't searching yet. Meta creates the demand Search later captures, and its retargeting closes the wary first-time buyer (the hardest objection: trusting a new brand). [STRATEGY][BRAND objections] It carries the most budget because it does the most jobs (reach + consideration + retarget).
- **Campaign structure (CBO vs ABO):** Use **ABO (ad-set budget)** at launch for control on a thin budget — CBO can starve a test cell before it gets a read. [REC] Three campaigns:
  1. **Prospecting — Conversions.** 2–3 ad sets max (don't over-fragment SGD-thin audiences):
     - **Interest stack (broad-ish):** specialty coffee, home brewing / pour over, coffee grinders/scales (gear-led enthusiasts [RESEARCH]), single-origin coffee, espresso at home; layered to SG, English, age ~25–55. [RESEARCH segments]
     - **Engaged shoppers / DTC behaviours:** "engaged shoppers" behaviour + coffee interests. [REC]
     - **Broad / advantage+ test (1 ad set):** minimal targeting, let the algorithm find buyers off the creative + pixel — often the most efficient cell on small budgets if creative is strong. [REC]
  2. **Retargeting — Conversions (turned ON per the trigger in §5, ~week 2–3).** Audiences: site visitors (180-day), product/landing-page viewers, add-to-cart non-purchasers, IG/FB engagers (365-day), video viewers (75%+ of the hero video — these are your warmest, since they consumed the proof). [CREATIVE A1] *Why retargeting matters most here:* a cold audience rarely buys an unknown premium brand first-touch; retargeting + the guarantee is where the wary convert. [BRAND]
  3. **(Phase 2) Lookalike — Conversions.** **1% LAL of purchasers**, and **1% LAL of add-to-cart / high-value site visitors** as a fallback until purchaser volume is large enough to seed a LAL (Meta needs ~100+ seed events; we likely won't hit that for purchasers, so **the value-based / engagement LAL is the realistic one** [ASSUMPTION]). Turn on only once a seed audience exists (~week 4–5). [REC]
- **Placements:** **Advantage+ placements (automatic)** to let Meta find cheap impressions, BUT review the placement breakdown weekly and exclude Audience Network if it shows junk traffic (high CTR, zero conversions). Creative is built 9:16/4:5/1:1 to serve Reels, Stories, Feed. [CREATIVE specs]
- **Geo / language:** Singapore, English. [DNA]
- **Budget rationale:** SGD 400 (40%). The biggest single deployed line because it does demand creation *and* retargeting and matches the visual offer. Held below the strategy's 45% so more goes into the flexible reserve (§2). Meta prospecting **only scales after the hero creative clears the ≥25% hook-rate KPI** — no spend behind unproven creative. [STRATEGY §4][CREATIVE]

### Channel C — Organic IG + SG community + editorial (earned trust / TOFU·MOFU)

- **Objective:** Earned reach + credibility a new brand cannot buy, and **a meaningful share of the 70 customers at zero marginal media cost** — this is what makes blended CAC ≤ SGD 14 arithmetically possible. [STRATEGY][GOAL]
- **Why it earns its (effort) budget:** Trust is the weakest link and there are no testimonials [BRAND]. Inclusion in the **Honeycombers / TheSmartLocal / SETHLUI / Best in Singapore / Time Out** roundup ecosystem is a recurring acquisition path competitors use [RESEARCH], and SG coffee communities (Homeground/Joo Chiat, Nylon/Everton Park, Fluid Collective; Singapore Coffee Week; National Coffee Championship orbit) concentrate exactly the high-intent enthusiasts the trio is built for. [RESEARCH]
- **Tactics (effort, not paid):**
  - **Editorial outreach (weeks 1–2):** pitch the trio + the Asian-origin-discovery + ≥6-week-guarantee angle to the named publishers for "best roasters / best coffee subscriptions / new launches" inclusion. Use the editorial visual kit (A11). [CREATIVE]
  - **Organic IG (weeks 1–8):** the A10 launch set + ongoing tier/origin/process education, targeting ≥4% engagement. [CREATIVE]
  - **Community seeding (weeks 1–4):** participate authentically in SG coffee communities/events; **verify Reddit r/singapore and Telegram groups on-platform first — research flagged these as plausible-but-unverified; do not rely on them until confirmed.** [RESEARCH gap]
- **Tracking:** dedicated UTMs + a discount-free **trackable code or "where did you hear about us" field** at checkout to attribute organic/earned purchases (see §3). *Why:* without attribution, organic's contribution is invisible and the blended-CAC story can't be validated.
- **Budget:** SGD 0 paid. **Risk flag:** this is the plan's biggest dependency and the least controllable lever — see Risks.

### Channel D — Retargeting + scale reserve (held budget / RETARGET + scale)

- **This is partly a channel (retargeting) and partly an un-committed reserve.** Retargeting runs inside Meta (Channel B campaign 2). The **reserve** is budget deliberately *not* deployed until the week-3 read tells us where SGD goes furthest. [STRATEGY §3, §4, §6]
- **Why a 30% reserve (vs. the strategy's indicative 20%):** on a no-baseline launch, the single highest-leverage decision is concentrating money behind the proven low-CAC channel *after* you've seen real data — not guessing the split up front. A larger reserve buys that optionality. The week-1–2 deployed split still puts both paid channels live per strategy. [STRATEGY intent; REC on the exact %]
- **Budget:** SGD 300 (30%), released weeks 3–8 (see §2 pacing and §5 trigger).

---

## 2. Budget allocation & pacing

*Framework: unit-economics / CAC-payback model. All SGD figures are planning targets; benchmarks flagged `[ASSUMPTION]` pending live data.*

### Final channel split (SGD 1,000 total paid)

| Channel | % | SGD | Role | Why this share |
|---|---|---|---|---|
| Google Search | 30% | **300** | Intent capture (BOFU) | Lowest-CAC ready buyers; focused non-brand set + brand defence. Scale candidate. |
| Meta/IG paid | 40% | **400** | Demand creation + retargeting | Most jobs (reach + consider + retarget); matches the visual offer. |
| Retargeting + scale reserve | 30% | **300** | Held; deploy to the winner after wk-3 read | Optionality is the highest-leverage move with no baseline. |
| Organic IG + community + editorial | — | **0 (effort)** | Earned trust + ~40% of volume | Makes blended CAC ≤ SGD 14 possible at zero media cost. |
| **Total paid** | **100%** | **1,000** | | |

### Pacing by phase (8 weeks)

*Front-load testing into weeks 1–4 across both paid channels; hold the reserve; release it to the winner weeks 4–8.* [STRATEGY §4, §6]

| | Weeks 1–2 (Launch & learn) | Weeks 3–4 (Read & reallocate) | Weeks 5–8 (Scale proof) | Total |
|---|---|---|---|---|
| **Google Search** | 80 | 90 | 130 | **300** |
| **Meta/IG prospecting** | 120 | 110 | 70 | **300** |
| **Meta/IG retargeting** | 0 | 40 | 60 | **100** |
| **Reserve → winner** | 0 | 60 | 240 | **300** |
| **Weekly-equivalent paid** | ~100/wk | ~150/wk | ~125/wk | |
| **Phase total** | **200** | **300** | **500** | **1,000** |

Notes:
- **Weeks 1–2 spend lightly (~SGD 100/wk)** — gather conversion data across both channels before committing; don't blow budget before the hero creative clears hook-rate. [STRATEGY §4]
- **Retargeting turns on ~end of week 2 / week 3** once an audience has pooled (see §5 trigger).
- **The reserve front-loads into weeks 5–8** behind whichever channel posted the lowest cost-per-purchase at the week-3 read.
- **Floor discipline:** keep each test channel funded long enough for a valid-ish read before cutting (see statistical caveat). Don't zero a channel on week-1 noise. [STRATEGY §4]

### Unit economics — the path to 70 customers

**Targets (from goal):** 70 customers / 8 weeks; blended CAC ≤ SGD 14; paid cost-per-purchase ≤ SGD 25; AOV ≥ SGD 50; LP CVR ≥ 3%. [GOAL]

**Step 1 — what SGD 1,000 buys on paid.**
At the **target** paid cost-per-purchase of SGD 25: 1,000 ÷ 25 = **40 paid customers** (the floor that still hits the marketing KPI).
At a **stretch** blended paid cost-per-purchase of ~SGD 22 (achievable if Search comes in cheap and retargeting is efficient): 1,000 ÷ 22 ≈ **45 paid customers**.
→ **Paid contributes ~40–45 customers.** [Matches goal's "paid drives ~35–45 of the 70" — GOAL]

**Step 2 — what organic/earned must contribute.**
70 − (40 to 45) = **25 to 30 customers from organic/earned + the brand-search halo** at ~zero marginal media cost. [STRATEGY][GOAL]

**Step 3 — blended CAC check.**
Blended CAC = total paid spend ÷ total customers = **1,000 ÷ 70 = SGD 14.3.**
→ Hits ≤ SGD 14 **only if total customers reach ~71–72** (1,000 ÷ 72 = SGD 13.9). So the real operating target is **~72 customers** to clear CAC with margin — i.e. the 70 goal and the ≤ SGD 14 CAC are the *same constraint expressed two ways*, and **both depend on organic delivering its ~25–30.** If organic underdelivers (say 15), blended CAC rises to 1,000 ÷ 55 = **SGD 18.2**, missing the target. This is the central risk. [GOAL][see Risks]

**Step 4 — funnel volume implied (sanity check on traffic).**
At LP CVR 3% [GOAL], 40–45 paid purchases require **~1,300–1,500 paid sessions** to the landing page over 8 weeks (45 ÷ 0.03 ≈ 1,500). Across SGD 700 of deployed acquisition spend (Search 300 + Meta prospecting 300 + retargeting 100), that implies a **blended cost-per-LP-session of ~SGD 0.45–0.55** — aggressive but plausible if Search CPCs land ~SGD 0.80–1.50 and Meta CPCs ~SGD 0.40–0.90. **If real CPCs/CVR are worse, the 40–45 figure compresses and organic must carry more.** Monitor cost-per-session and LP CVR from day one. [ASSUMPTION — no baseline]

**Step 5 — AOV / revenue margin context (not a goal KPI but a viability check).**
At AOV ≥ SGD 50 (trio) [GOAL] and 70 customers → ~SGD 3,500 first-purchase revenue against SGD 1,000 media + COGS. **Trio economics are `<TO CONFIRM>` [DNA/GOAL]** — if the trio's contribution margin doesn't comfortably exceed SGD 14 CAC, the unit economics break regardless of media performance. **Flag to orchestrator: confirm trio gross margin before launch.**

---

## 3. KPI plan & instrumentation

*Framework: three-tier KPI cascade (Business → Marketing → Creative). Each tier has a target, a tracking source, and a cadence.*

### The three tiers (with targets and where each is read)

| Tier | KPI | Target | Read from |
|---|---|---|---|
| **Business** | New customers (8 wks) | **70** (operating target ~72 for CAC margin) | Shopify/commerce: new vs returning customer report |
| **Business** | Blended CAC | **≤ SGD 14** | Total paid spend ÷ total new customers |
| **Business** | AOV | **≥ SGD 50** | Commerce platform AOV (trio) |
| **Marketing** | Landing-page CVR | **≥ 3%** | GA4: purchases ÷ LP sessions |
| **Marketing** | Paid cost-per-purchase | **≤ SGD 25** | Meta Ads Mgr + Google Ads (purchase conv ÷ spend) |
| **Marketing** | Paid-social CTR | **≥ 1.0%** | Meta Ads Manager (link CTR) |
| **Creative** | Hook rate (3-sec/thumb-stop) | **≥ 25%** | Meta: 3-sec video plays ÷ impressions, per opener variant [CREATIVE A1] |
| **Creative** | Organic engagement rate | **≥ 4%** | IG insights / native analytics |

### Supporting funnel metrics to watch (diagnostic, not goal KPIs)

Impressions → CTR → CPC → LP sessions → **Add-to-Cart rate** → **Checkout-initiated** → **Purchase (CVR)** → cost-per-purchase → CAC. Watching ATC and checkout-initiated tells you *where* the funnel leaks (creative vs. landing page vs. checkout) so optimization is diagnosed, not guessed. [REC]

### Instrumentation / setup (must be live and QA'd before spend)

1. **GA4** with **enhanced ecommerce** events (`view_item`, `add_to_cart`, `begin_checkout`, `purchase` with value + currency SGD). Mark `purchase` as a **key event/conversion**. This is the source of truth for LP CVR.
2. **Meta Pixel + Conversions API (CAPI).** CAPI is **not optional** — iOS/ITP signal loss makes pixel-only data unreliable; CAPI recovers purchase signal the algorithm needs to optimise on a thin budget. Dedup pixel + CAPI events. Verify `Purchase` fires with value/currency in Events Manager test mode. [REC]
3. **Google Ads conversion tracking:** import the GA4 `purchase` conversion **or** place the Google global site tag + a purchase conversion; set conversion value = order value. Use a single primary conversion (Purchase) for bidding.
4. **UTMs on every paid + organic link** — strict convention so attribution is clean:
   `utm_source` (google / meta / instagram / honeycombers / etc.) · `utm_medium` (cpc / paidsocial / organic / referral / editorial) · `utm_campaign` (coast-launch-2026) · `utm_content` (asset/opener variant, e.g. `a1-proof-hook`) · `utm_term` (keyword, Search only).
5. **Organic/earned attribution:** because earned customers won't carry click attribution reliably, add a **post-purchase "How did you hear about us?" field** at checkout (free-text or pick-list incl. "friend / IG / a website article / search"). *Why:* this is the only practical way to validate the ~25–30 organic customers the CAC math depends on. [GOAL][see §2 Step 3]
6. **Naming & UTM map** documented in one sheet so weekly reporting reconciles Ads Manager spend ↔ GA4 sessions ↔ Shopify orders.

### Reporting cadence

- **Daily (first 10 days, then as needed):** spend pacing, that conversions are *firing at all* (catch tracking breakage early), no runaway CPCs. 5-minute glance.
- **Weekly (every Monday):** the full three-tier scorecard above + funnel diagnostics, per channel and per creative variant. This is the decision meeting.
- **Week-3 read (the reallocation gate):** formal review of cost-per-purchase by channel → decide reserve deployment (§5).
- **End-of-flight (week 8):** final scorecard vs. all three tiers; capture learnings into `knowledge/performance/` for the next flight (future capability).

---

## 4. Campaign setup recommendations

### Naming convention (consistency = clean reporting)

`COAST | {channel} | {funnel} | {phase} | {audience-or-keyword}`
e.g. `COAST | META | PROSPECT | P1 | interest-specialty`; `COAST | GADS | NONBRAND | P1 | asian-origin`; `COAST | META | RETARGET | P2 | atc-nonpurch`. Ad/creative level carries the opener variant (`a1-proof`, `a1-curiosity`, `a1-reframe`) so hook-rate is comparable. [CREATIVE]

### Bid strategies (thin-budget appropriate)

- **Google Search:** start **Maximise Conversions** (no tCPA target until ~15–30 conversions exist; tCPA ≤ SGD 25 once stable — may never trigger at this budget, in which case stay on Max Conversions with manual CPC caps). Brand campaign can run **Manual/Max Clicks** cheaply. [REC]
- **Meta:** **Lowest cost (no cap)** at launch to let the algorithm learn; introduce a **cost cap ~SGD 25** only after exiting the learning phase, if volume allows. **Optimise for Purchase**; fall back to Add-to-Cart only if Purchase volume is too low to exit learning. [REC]

### Conversion events / learning budgets

- **Primary event everywhere: Purchase** (value-tracked, SGD). Secondary/diagnostic: Add-to-Cart, Begin-Checkout.
- **Meta learning-phase reality check:** Meta needs **~50 optimisation events per ad set per week** to exit learning. At our budget we will **almost certainly not reach that on Purchase.** Mitigations: (a) **few ad sets, consolidated budget** (don't fragment); (b) optimise on a higher-funnel event (ATC) if Purchase is too sparse; (c) accept that the account runs in extended learning and treat reads as directional. **Flag this explicitly — it is the core constraint of a SGD 1,000 Meta budget.** [REC][caveat]
- **Minimum viable daily budget per Meta ad set:** ~SGD 8–12 so each cell can clear a few clicks/day; this is why we cap at **2–3 prospecting ad sets** — more would starve all of them.

### Pre-launch tracking / QA checklist

- [ ] GA4 `purchase` (and ATC/checkout) events fire with correct value + SGD currency (real test order).
- [ ] GA4 `purchase` marked as key event/conversion.
- [ ] Meta Pixel **and** CAPI both fire `Purchase`; deduplicated; verified in Events Manager test events.
- [ ] Google Ads conversion (Purchase) imported/firing; conversion value populated; single primary conversion for bidding.
- [ ] UTM convention applied to **every** paid + organic + editorial link; test one click end-to-end into GA4.
- [ ] Checkout "How did you hear about us?" field live and writing to order data.
- [ ] Search negatives loaded (cheap/free/jobs/machine/etc.); Search Partners + Display **off**; geo = Singapore; language = English.
- [ ] Meta geo = Singapore, English; Audience Network reviewed; placements set; retargeting audiences **created** (even if paused) so they start pooling day one.
- [ ] Landing page passes: mobile speed, guarantee adjacent to buy button, trio + guarantee lockup present, no fabricated testimonial in the review slot. [CREATIVE A8]
- [ ] Hero video (A1) live with the **three openers as separate ads** so hook-rate is measured per variant. [CREATIVE]
- [ ] Conversion tracking sanity: place a real test order, confirm it appears in GA4 + Meta + Google + Shopify before scaling spend.
- [ ] Budgets/pacing set to Phase-1 figures; reserve held (not deployed).
- [ ] **Trio gross margin confirmed > SGD 14** (orchestrator action; viability gate). [DNA/GOAL `<TO CONFIRM>`]

---

## 5. Optimization plan

*Data-driven decision rules for weeks 1–8. Statistical caveat governs all of it (below).*

### Weeks 1–2 — Launch & learn

- **Goal:** get clean data flowing, clear the creative gate, don't overspend. ~SGD 100/wk deployed.
- **Creative gate (hard rule):** **no prospecting scale until the hero video's best opener clears hook rate ≥ 25%.** [STRATEGY §4][CREATIVE] If none of the three openers clears 25% by end of week 2, **pause paid prospecting scale, keep spend minimal, and brief Creative for new openers** — scaling weak creative wastes the whole budget.
- **Watch, don't react hard:** record CTR, CPC, ATC rate, LP CVR, cost-per-purchase per channel/variant. Avoid killing anything on <1 week of noise.
- **Retargeting turn-on trigger:** enable the retargeting campaign once the **remarketing pool ≥ ~300–500 users** (site visitors + video viewers) — typically **end of week 2 / start of week 3**. Turning it on earlier wastes budget on too-small an audience. [REC]

### Week-3 read — the reallocation gate (the strategy's core rule, finalised)

Compute **cost-per-purchase per channel** (and per major audience/keyword theme) over weeks 1–3. Then:

1. **Identify the lowest cost-per-purchase channel** that is **at or below SGD 25** and has produced **≥ ~5 purchases** (minimum credible signal — below this, treat as too-noisy and lean on the directional trend + funnel metrics, not the point estimate). [caveat]
2. **Deploy the held reserve (SGD 300) primarily to that winner** across weeks 4–8 (front-loaded weeks 5–8 per §2 pacing). [STRATEGY §6]
3. **Cut or shrink any channel running > SGD 25 cost-per-purchase with no improving trend** — reallocate its remaining budget to the winner. But **do not zero a channel purely on thin volume**; if cost-per-purchase is high *but* CTR/ATC are healthy and the trend is improving, give it one more week before cutting (learning-phase effects). [caveat]
4. **If both channels are ≤ SGD 25:** split the reserve ~60/40 toward the cheaper one, keep both alive (diversification protects against one channel fatiguing).
5. **If neither channel is ≤ SGD 25 by week 3:** this is the warning state. Actions in priority order: (a) shift budget to **retargeting** (warm traffic converts cheapest); (b) tighten Search to only the best-converting keyword themes; (c) escalate **organic/editorial** effort to carry more volume; (d) flag to orchestrator that the 70-customer target is at risk and revisit the offer/landing page (CVR < 3% means a page/offer problem, not a media problem). [GOAL at risk]

### Weeks 5–8 — Scale proof + fold in testimonials

- **Scale the winner** with the reserve; keep retargeting funded (it should be the most efficient line by now).
- **Fold in harvested testimonials (the strategy's weeks-3–4 harvest → weeks-5–8 use):**
  - The post-purchase review/UGC request runs from first orders (weeks 2–3 onward). **Mechanism owner flag:** strategy/creative assigned the *capture* to performance/orchestrator — set up an **automated post-delivery email/SMS requesting a review** (timed ~1–2 weeks post-purchase so beans have been brewed), plus a simple incentive-free ask. [STRATEGY §6][BRAND][CREATIVE §5]
  - As real reviews arrive, **populate the B-series creative slots** (B1 social-proof ad, B2 retargeting closer, B3 landing-page review module) — **real content only, never fabricated.** [CREATIVE no-fabrication mandate]
  - **Prioritise injecting social proof into retargeting and the landing page first** — that's where the wary, already-warm buyer decides, so proof has the highest marginal conversion impact there. [BRAND: trust is the weakest link]
- **Refresh fatiguing creative:** if frequency climbs (>~2.5–3) and CTR/cost-per-purchase degrade, rotate in the new social-proof creative — this doubles as the fatigue fix and the proof injection.

### Ongoing optimization rules (all weeks)

- **Search:** mine the search-terms report weekly → add negatives (kill waste), promote high-converting queries to their own tight ad group. Pause keywords with spend > ~SGD 20 and zero conversions.
- **Meta:** kill ad *variants* (not whole ad sets) that underperform on CTR/hook-rate; let the algorithm consolidate spend on winners. Don't restart learning by editing live ad sets unnecessarily.
- **Landing page:** if traffic is healthy but **LP CVR < 3%**, the bottleneck is the page/offer, not media — prioritise fixing it (guarantee prominence, trio clarity, checkout friction) over buying more traffic. [GOAL marketing KPI]

### Statistical-validity caveat (must read)

At ~SGD 125/week and dozens (not hundreds/thousands) of conversions over 8 weeks, **no A/B test here will reach statistical significance.** All decisions are **directional and guardrail-based**, weighted by funnel diagnostics and trend, not p-values. Concretely: (a) prefer **fewer, better-funded cells** over many under-powered ones; (b) require a **minimum purchase count (~5)** before trusting a cost-per-purchase point estimate; (c) **bias against premature killing** — learning-phase noise looks like failure; (d) treat every benchmark in this plan as a **hypothesis to be replaced by live data**, since the DNA has **no baseline metrics** to anchor them. [DNA `<TO CONFIRM>`]

---

## Assumptions & flags (honest)

1. **No baseline metrics in DNA (`<TO CONFIRM>`)** — every SGD benchmark (CPC, CVR, cost-per-purchase) is an `[ASSUMPTION]` to be validated against live data in weeks 1–2; targets are the goal's, not historical.
2. **Trio economics unconfirmed (~SGD 50–54)** — the CAC ≤ SGD 14 target is only viable if trio **gross margin comfortably exceeds SGD 14**. **Confirm before launch** (orchestrator gate). [DNA/GOAL]
3. **Organic must deliver ~25–30 of the 70 customers** at ~zero media cost. This is the plan's largest dependency and least controllable lever; if it underdelivers, blended CAC misses ≤ SGD 14 (see §2 Step 3). Mitigation: aggressive editorial/community effort + retargeting + the post-purchase attribution field to measure it.
4. **Meta will likely run in extended learning** (won't hit ~50 purchase events/ad set/week at this budget). Reads are directional; consolidation and possibly ATC-optimisation are mitigations. [§4]
5. **Reddit/Telegram SG communities unverified** [RESEARCH] — verify on-platform before relying; not budgeted as load-bearing.
6. **Language = English-primary** assumed per DNA; Mandarin/Malay reach unvalidated — not targeted in this plan. [DNA]
7. **Channel split nudged to 30/40/30** from the strategy's indicative 35/45/20 — a larger held reserve for optionality on a no-baseline launch. Within the strategy's §6 delegation of detail; flag for orchestrator sign-off if the original 20% reserve is preferred.

---

## Knowledge gaps (flagged honestly)

1. **`knowledge/performance/` is a stub** — no project-defined channel benchmarks, KPI-target model, budget model, or optimization heuristics. I applied standard frameworks (full-funnel channel-role model, three-tier KPI cascade, unit-economics/CAC model) and labelled them; SG-specific CPC/CVR/cost-per-purchase benchmarks should be filled in here after this flight to make future planning evidence-anchored rather than assumption-anchored.
2. **No baseline metrics / no prior-channel results** [DNA `<TO CONFIRM>`] — benchmarks are unanchored; this flight's actuals are the first dataset.
3. **Trio gross margin not confirmed** — unit-economics viability gate sits outside this plan's authority.

---

## Pre-launch checklist (consolidated — all must pass before spend)

- [ ] Trio gross margin confirmed > SGD 14 (viability gate). [orchestrator]
- [ ] GA4 ecommerce events + `purchase` key event firing correctly (real test order).
- [ ] Meta Pixel + CAPI `Purchase` firing, deduped, verified.
- [ ] Google Ads Purchase conversion firing with value.
- [ ] UTM convention applied to all paid/organic/editorial links; one click tested into GA4.
- [ ] Checkout "How did you hear about us?" field live.
- [ ] Search: negatives loaded, Search Partners + Display off, geo SG / English, phrase+exact only.
- [ ] Meta: 2–3 prospecting ad sets, retargeting audiences created (pooling), geo SG / English, Purchase optimisation.
- [ ] Hero video live as 3 separate openers for per-variant hook-rate measurement.
- [ ] Landing page QA: mobile speed, guarantee by buy button, trio + guarantee lockup, no fabricated testimonial.
- [ ] Budgets set to Phase-1 pacing; SGD 300 reserve held.
- [ ] Weekly three-tier scorecard sheet built; UTM/spend/orders reconciliation map documented.
- [ ] Creative gate understood: no prospecting scale until an A1 opener clears hook rate ≥ 25%.
```


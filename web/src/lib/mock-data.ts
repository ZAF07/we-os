import type { Status } from "@/lib/status";

export const STAGE_NAMES = [
  "Brief",
  "Research",
  "Strategy",
  "Plan",
  "Produce",
  "Approve",
  "Publish",
  "Measure",
] as const;

export const STRATEGY_STAGE_INDEX = STAGE_NAMES.indexOf("Strategy");

export const WORKSPACE_SLUG = "fernway-refill-launch";

export interface CalendarItem {
  day: number;
  dow: string;
  title: string;
  channel: string;
  campaign: string;
  audience: string;
  funnel: string;
  pillar: string;
  status: Status;
  perf: string;
}

export const CALENDAR_ITEMS: CalendarItem[] = [
  {
    day: 9,
    dow: "Thu",
    title: "Reel · Refill in 15 seconds",
    channel: "Instagram",
    campaign: "Fernway Refill Launch",
    audience: "Low-waste households",
    funnel: "Awareness",
    pillar: "Refill economics",
    status: "Published",
    perf: "3.1% CTR · 41k reach",
  },
  {
    day: 13,
    dow: "Mon",
    title: "Email · Welcome series #2",
    channel: "Email",
    campaign: "Loyalty Newsletter",
    audience: "New customers",
    funnel: "Retention",
    pillar: "Designed to stay",
    status: "Published",
    perf: "52% open · 6.4% click",
  },
  {
    day: 16,
    dow: "Thu",
    title: "Reel · Cost-per-clean math",
    channel: "Instagram",
    campaign: "Fernway Refill Launch",
    audience: "Low-waste households",
    funnel: "Awareness",
    pillar: "Refill economics",
    status: "Scheduled",
    perf: "",
  },
  {
    day: 17,
    dow: "Fri",
    title: "Email · Restock reminder",
    channel: "Email",
    campaign: "Loyalty Newsletter",
    audience: "Repeat buyers",
    funnel: "Retention",
    pillar: "No compromise",
    status: "Ready for review",
    perf: "",
  },
  {
    day: 20,
    dow: "Mon",
    title: "Blog · True cost of single-use",
    channel: "Blog / SEO",
    campaign: "Fernway Refill Launch",
    audience: "Researchers",
    funnel: "Consideration",
    pillar: "Refill economics",
    status: "In progress",
    perf: "",
  },
  {
    day: 21,
    dow: "Tue",
    title: "Carousel · Bottle design story",
    channel: "Instagram",
    campaign: "Summer Refill Drop",
    audience: "Design-led shoppers",
    funnel: "Consideration",
    pillar: "Designed to stay",
    status: "Draft",
    perf: "",
  },
  {
    day: 23,
    dow: "Thu",
    title: "Newsletter · July edition",
    channel: "Email",
    campaign: "Loyalty Newsletter",
    audience: "All subscribers",
    funnel: "Retention",
    pillar: "Mixed",
    status: "Scheduled",
    perf: "",
  },
  {
    day: 27,
    dow: "Mon",
    title: "YouTube cutdown · Demo 30s",
    channel: "YouTube",
    campaign: "Summer Refill Drop",
    audience: "Low-waste households",
    funnel: "Awareness",
    pillar: "No compromise",
    status: "Draft",
    perf: "",
  },
  {
    day: 29,
    dow: "Wed",
    title: "Carousel · Efficacy results",
    channel: "Instagram",
    campaign: "Summer Refill Drop",
    audience: "Skeptics",
    funnel: "Consideration",
    pillar: "No compromise",
    status: "Needs input",
    perf: "",
  },
];

/**
 * Strips the format prefix from a calendar item title.
 *
 * Args:
 *   title: A title such as "Reel · Refill in 15 seconds".
 *
 * Returns:
 *   The short title after the "·" separator, or the full title.
 */
export function shortTitle(title: string): string {
  return title.split("· ")[1] ?? title;
}

export type QueueTag = "Decision" | "Flagged" | "Needs input";

export interface QueueItem {
  key: string;
  tag: QueueTag;
  title: string;
  meta: string;
  due: string;
  cta: string;
  href: string;
  brandSection?: number;
}

const QUEUE_ALL: QueueItem[] = [
  {
    key: "pos",
    tag: "Decision",
    title: "Approve audience & positioning",
    meta: "Fernway Refill Launch · Strategy stage",
    due: "Due today",
    cta: "Review",
    href: `/campaigns/${WORKSPACE_SLUG}`,
  },
  {
    key: "plan",
    tag: "Decision",
    title: "Approve content plan (14 items)",
    meta: "Summer Refill Drop · Plan stage",
    due: "Due Fri",
    cta: "Review",
    href: "/campaigns/summer-refill-drop",
  },
  {
    key: "flag",
    tag: "Flagged",
    title: 'Carousel copy uses restricted claim "non-toxic"',
    meta: "Summer Refill Drop · Produce stage",
    due: "Blocking 1 asset",
    cta: "Resolve",
    href: "/brand",
    brandSection: 6,
  },
  {
    key: "input",
    tag: "Needs input",
    title: "Confirm July budget split across channels",
    meta: "Earth Month Retargeting · Plan stage",
    due: "2 days idle",
    cta: "Provide",
    href: "/campaigns/earth-month-retargeting",
  },
  {
    key: "sched",
    tag: "Decision",
    title: "Approve publishing schedule",
    meta: "Loyalty Newsletter · Publish stage",
    due: "Due Mon",
    cta: "Review",
    href: "/campaigns/loyalty-newsletter",
  },
];

/**
 * Returns the Home action queue, reflecting the approve flag.
 *
 * Args:
 *   approved: Whether the Fernway Strategy stage has been approved.
 *
 * Returns:
 *   The four queue items the operator should see, per the prototype.
 */
export function queueItems(approved: boolean): QueueItem[] {
  if (approved) return QUEUE_ALL.filter((item) => item.key !== "pos");
  return QUEUE_ALL.slice(0, 4);
}

export type StatTone = "default" | "primary" | "destructive";

export interface HomeStat {
  label: string;
  value: string;
  tone: StatTone;
}

/**
 * Returns the four Home stat cards, reflecting the approve flag.
 *
 * Args:
 *   approved: Whether the Fernway Strategy stage has been approved.
 *
 * Returns:
 *   Stat cards exactly as defined by the design prototype.
 */
export function homeStats(approved: boolean): HomeStat[] {
  return [
    {
      label: "Pending approvals",
      value: approved ? "3" : "4",
      tone: "primary",
    },
    { label: "Active campaigns", value: "4", tone: "default" },
    { label: "Scheduled this week", value: "5", tone: "default" },
    { label: "Blocked", value: "2", tone: "destructive" },
  ];
}

export interface ActiveCampaign {
  slug: string;
  name: string;
  status: Status;
  pct: string;
  stageNote: string;
}

/**
 * Returns the Home in-progress campaign list, reflecting the approve flag.
 *
 * Args:
 *   approved: Whether the Fernway Strategy stage has been approved.
 *
 * Returns:
 *   Active campaigns exactly as defined by the design prototype.
 */
export function activeCampaigns(approved: boolean): ActiveCampaign[] {
  return [
    {
      slug: WORKSPACE_SLUG,
      name: "Fernway Refill Launch",
      status: approved ? "In progress" : "Ready for review",
      pct: approved ? "44%" : "31%",
      stageNote: approved
        ? "Plan · drafting channel strategy"
        : "Strategy · awaiting your approval",
    },
    {
      slug: "summer-refill-drop",
      name: "Summer Refill Drop",
      status: "In progress",
      pct: "56%",
      stageNote: "Produce · 3 of 14 assets drafted",
    },
    {
      slug: "loyalty-newsletter",
      name: "Loyalty Newsletter",
      status: "In progress",
      pct: "75%",
      stageNote: "Publish · schedule pending approval",
    },
  ];
}

export interface BlockedItem {
  title: string;
  reason: string;
  cta: string;
  href: string;
  brandSection?: number;
}

export const BLOCKED_ITEMS: BlockedItem[] = [
  {
    title: "Earth Month Retargeting",
    reason: "Waiting on budget confirmation since Jul 14",
    cta: "Provide input",
    href: "/campaigns/earth-month-retargeting",
  },
  {
    title: "Efficacy carousel",
    reason: "Claim substantiation missing — legal evidence required",
    cta: "Attach evidence",
    href: "/brand",
    brandSection: 4,
  },
];

export interface Finding {
  text: string;
  src: string;
}

export const FINDINGS: Finding[] = [
  {
    text: "Demo-video formats outperform static posts 3.1× on CTR with the core segment.",
    src: "From 6 published assets · Jun 12 – Jul 9",
  },
  {
    text: "Competitor Grove shifted messaging to price this month — overlap risk on pillar 1.",
    src: "Competitor scan · Jul 14",
  },
  {
    text: '"Refill economics" subject lines lift email opens +9pts vs. sustainability framing.',
    src: "A/B result · n=8,400 · Jul 8",
  },
];

export interface PerfStat {
  label: string;
  value: string;
  delta: string;
}

export const HOME_PERF_STATS: PerfStat[] = [
  { label: "Reach", value: "412k", delta: "+22%" },
  { label: "Engaged CTR", value: "2.4%", delta: "+0.3" },
  { label: "CAC", value: "$18.20", delta: "−8%" },
];

export interface Recommendation {
  text: string;
  href: string;
}

export const RECOMMENDATIONS: Recommendation[] = [
  {
    text: "Shift 2 static posts to the demo-video format",
    href: "/performance",
  },
  {
    text: "Review positioning vs. Grove's new price message",
    href: `/campaigns/${WORKSPACE_SLUG}`,
  },
];

/**
 * Returns the Home "Scheduled next" list derived from the calendar items.
 *
 * Returns:
 *   Calendar items falling between July 16 and 23, per the prototype.
 */
export function upcomingItems(): CalendarItem[] {
  return CALENDAR_ITEMS.filter((item) => item.day >= 16 && item.day <= 23);
}

/**
 * Returns a stage's canonical status, reflecting the approve flag.
 *
 * Args:
 *   stage: Stage index 0–7.
 *   approved: Whether the Fernway Strategy stage has been approved.
 *
 * Returns:
 *   The stage's status per the prototype's stageStatus logic.
 */
export function stageStatus(stage: number, approved: boolean): Status {
  if (stage < 2) return "Approved";
  if (stage === 2) return approved ? "Approved" : "Ready for review";
  if (stage === 3) return approved ? "In progress" : "Not started";
  return "Not started";
}

/**
 * Returns the per-stage subtitle lines, reflecting the approve flag.
 *
 * Args:
 *   approved: Whether the Fernway Strategy stage has been approved.
 *
 * Returns:
 *   Eight subtitle strings, one per stage.
 */
export function stageSubtitles(approved: boolean): string[] {
  return [
    "Approved Jul 2",
    "Approved Jul 8",
    approved ? "Approved just now" : "Awaiting your decision",
    approved ? "Drafting — today 4pm" : "Starts after Strategy",
    "Not started",
    "Not started",
    "Not started",
    "Not started",
  ];
}

export interface StageDetail {
  title: string;
  desc: string;
  done: string[];
  inputs: string[];
  after: string;
}

/**
 * Returns the detail document for a non-Strategy stage.
 *
 * Args:
 *   stage: Stage index 0–7 (Strategy, index 2, is rendered as its own
 *     document and falls back to the Plan detail per the prototype).
 *   approved: Whether the Fernway Strategy stage has been approved.
 *
 * Returns:
 *   The stage's detail content per the prototype's stageDetails.
 */
export function stageDetail(stage: number, approved: boolean): StageDetail {
  const details: Record<number, StageDetail> = {
    0: {
      title: "Campaign brief",
      desc: "The goal, budget and constraints this campaign was created from.",
      done: [
        "Objective: 1,500 new refill subscriptions in Q3",
        "Budget: $48k across paid + owned",
        "Constraints logged: no discount-led messaging",
      ],
      inputs: ["None — brief approved Jul 2"],
      after:
        "Research ran against this brief; changing it re-opens Research and Strategy.",
    },
    1: {
      title: "Research readout",
      desc: "What the system learned before proposing a strategy — every claim links to a source.",
      done: [
        "14 sources analyzed: surveys, analytics, 6 interviews",
        "Competitor scan: Grove, Blueland, Branch Basics",
        "Price-sensitivity model built from purchase data",
      ],
      inputs: ["None — readout approved Jul 8"],
      after:
        "Findings feed the Strategy stage; new evidence can be attached any time.",
    },
    3: {
      title: "Channel & content plan",
      desc: "How the approved strategy becomes scheduled work: channels, budget split, content mix.",
      done: approved
        ? ["Channel strategy draft in progress (est. today 4pm)"]
        : ["Nothing yet — waiting on Strategy approval"],
      inputs: [
        "Confirm any channel you want excluded",
        "Confirm July flight dates",
      ],
      after:
        "You approve the channel strategy, then the content plan — before anything is produced.",
    },
    4: {
      title: "Production",
      desc: "Assets drafted from the approved plan, each scored for brand alignment.",
      done: ["Not started"],
      inputs: ["Asset-level approvals as drafts arrive"],
      after: "Approved assets move to the publishing schedule.",
    },
    5: {
      title: "Final approval",
      desc: "A single gate reviewing everything scheduled before it goes live.",
      done: ["Not started"],
      inputs: ["Final sign-off"],
      after: "Publishing unlocks.",
    },
    6: {
      title: "Publishing schedule",
      desc: "When and where each approved asset ships.",
      done: ["Not started"],
      inputs: ["Approve the schedule"],
      after:
        "Assets publish automatically at their slots; you can pull any item until it ships.",
    },
    7: {
      title: "Measurement",
      desc: "Performance connected back to the assumptions this campaign was built on.",
      done: ["Not started"],
      inputs: ["None — starts after first publish"],
      after: "Findings feed recommendations and the next campaign's research.",
    },
  };
  return details[stage] ?? details[3];
}

export interface AiAction {
  key: "alt" | "challenge" | "explain" | "evidence" | "rewrite" | "brand";
  label: string;
}

export const AI_ACTIONS: AiAction[] = [
  { key: "alt", label: "Generate alternatives" },
  { key: "challenge", label: "Challenge this assumption" },
  { key: "explain", label: "Explain recommendation" },
  { key: "evidence", label: "Use stronger evidence" },
  { key: "rewrite", label: "Rewrite for this audience" },
  { key: "brand", label: "Check brand alignment" },
];

export const AI_NOTES: Partial<Record<AiAction["key"], string>> = {
  alt: "3 alternative positioning angles drafted (economics-led, design-led, performance-led). Open Compare versions to review them side by side.",
  challenge:
    'Weakest assumption: "price sensitivity outweighs sustainability values." It rests on one 2025 survey (n=214). Suggest validating with a 2-day poll before Produce.',
  explain:
    "Economics-led positioning was chosen because it scored highest on purchase intent (S1), is unclaimed by the top 3 competitors (S4), and matches the winning email framing (S2).",
  evidence:
    "Found stronger support: replacing the 2024 industry stat with your own cohort data (repeat-purchase rate, n=3,120) strengthens pillar 1. Attached as S5, pending your review.",
  rewrite:
    'Rewritten for "Design-led shoppers": leads with the permanent-bottle story, moves cost-per-clean to support. Saved as an alternative version.',
};

export interface ScorecardRow {
  k: string;
  v: string;
  tone: "good" | "warn";
}

export const SCORECARD: ScorecardRow[] = [
  { k: "Voice & tone", v: "96%", tone: "good" },
  { k: "Claims backed", v: "4 of 5", tone: "warn" },
  { k: "Restricted language", v: "Clear", tone: "good" },
  { k: "Audience fit", v: "92%", tone: "good" },
];

export interface EvidenceSource {
  id: string;
  type: string;
  title: string;
  note: string;
}

export const EVIDENCE: EvidenceSource[] = [
  {
    id: "S1",
    type: "Survey",
    title: "Purchase-driver survey, May 2026",
    note: "n=214 · cost ranked #1 barrier at 61%",
  },
  {
    id: "S2",
    type: "A/B test",
    title: "Email subject-line framing test",
    note: "Economics framing +9pts open rate",
  },
  {
    id: "S3",
    type: "Interviews",
    title: "6 customer interviews, Jun 2026",
    note: "5 of 6 cited shipping waste + cost together",
  },
  {
    id: "S4",
    type: "Comp scan",
    title: "Competitor messaging audit",
    note: "Sustainability-first used by all 3 leaders",
  },
];

export interface BrandEntry {
  k: string;
  v: string;
  warn?: boolean;
  note?: string;
}

export interface BrandSection {
  name: string;
  verified: string;
  desc: string;
  entries: BrandEntry[];
}

export const BRAND_SECTIONS: BrandSection[] = [
  {
    name: "Positioning",
    verified: "Jul 2",
    desc: "The single idea Fernway owns and the frame every campaign starts from.",
    entries: [
      {
        k: "Category frame",
        v: 'Refill system for premium home care — not "eco cleaning products."',
      },
      {
        k: "Core promise",
        v: "Premium home care that costs less every month you keep it.",
        note: "Used by 3 active campaigns. Changing this re-opens their Strategy stages.",
      },
      {
        k: "Reason to believe",
        v: "Third-party efficacy results + published cost-per-clean data.",
      },
    ],
  },
  {
    name: "Products & services",
    verified: "Jun 28",
    desc: "What we sell, in the language we sell it in.",
    entries: [
      {
        k: "Starter Set",
        v: "Forever bottle + first 3 concentrate refills. Hero SKU, $42.",
      },
      {
        k: "Refill subscription",
        v: "Quarterly concentrate delivery. Core economics story — $0.31 per clean.",
      },
      {
        k: "Single refills",
        v: "One-off packs. Positioned as trial, never as the default.",
      },
    ],
  },
  {
    name: "Audience segments",
    verified: "Jul 8",
    desc: "Who we speak to, ranked by strategic priority.",
    entries: [
      {
        k: "1 · Low-waste households (28–45)",
        v: "Primary. Practical, cost-aware, already buying eco. Respond to economics over ethics.",
      },
      {
        k: "2 · Design-led shoppers",
        v: "Secondary. Buy the object first. Lead with the permanent-bottle story.",
      },
      {
        k: "3 · Skeptics",
        v: "Conversion segment. Need efficacy proof before price.",
      },
    ],
  },
  {
    name: "Voice & tone",
    verified: "Jun 28",
    desc: "How Fernway sounds, everywhere.",
    entries: [
      {
        k: "Plainspoken",
        v: "Short sentences. Real numbers. No euphemisms for price.",
      },
      {
        k: "Confident, not preachy",
        v: "We never guilt the reader about waste. The product argues for itself.",
      },
      {
        k: "Warm precision",
        v: 'Specific over superlative: "cleans marble, brass and glass" beats "works everywhere."',
      },
    ],
  },
  {
    name: "Claims & evidence",
    verified: "Jul 10",
    desc: "Every claim we make in public, with what backs it.",
    entries: [
      {
        k: '"Costs $0.31 per clean"',
        v: "Backed: internal pricing model, verified Jun 2026.",
      },
      {
        k: '"Outperforms leading brands on grease"',
        v: "Backed: third-party lab test, Mar 2026, on file.",
      },
      {
        k: '"Pays for itself in 4 months"',
        v: "Pending: needs the cost-per-clean substantiation attached before use.",
        note: "Currently blocking 1 asset in Summer Refill Drop.",
      },
    ],
  },
  {
    name: "Visual identity",
    verified: "Jun 15",
    desc: "The rules generated visuals are checked against.",
    entries: [
      {
        k: "Photography",
        v: "Natural light, real homes, product in use. Never studio-white backgrounds.",
      },
      {
        k: "Color",
        v: "Fern green + clay on warm neutrals. Accent used sparingly.",
      },
      {
        k: "Type",
        v: "One serif for headlines, one sans for everything else.",
      },
    ],
  },
  {
    name: "Restricted language",
    verified: "Jul 10",
    desc: "Words and claims that must never appear in published assets.",
    entries: [
      {
        k: '"Non-toxic"',
        v: 'Regulatory risk — replace with "plant-based formula, EPA Safer Choice certified."',
        warn: true,
      },
      { k: '"Chemical-free"', v: "Factually false. Never use.", warn: true },
      {
        k: '"Guaranteed"',
        v: "Only with the published guarantee terms linked.",
        warn: true,
      },
    ],
  },
  {
    name: "Competitors",
    verified: "Jul 14",
    desc: "Who we are compared against and how we differ.",
    entries: [
      {
        k: "Grove Collaborative",
        v: "Breadth play. Shifted to price messaging this month — overlap risk on pillar 1.",
      },
      {
        k: "Blueland",
        v: "Closest analog. Owns the tablet format; we own liquid concentrate + the bottle.",
      },
      {
        k: "Branch Basics",
        v: "Ingredient-purity story. Do not compete on purity claims.",
      },
    ],
  },
  {
    name: "Approved examples",
    verified: "Jul 9",
    desc: "The reference set new assets are scored against.",
    entries: [
      {
        k: 'Reel · "Refill in 15 seconds"',
        v: "Best performer to date — the pacing and math-on-screen format to emulate.",
      },
      {
        k: "Email · Welcome series #2",
        v: "Voice benchmark: plainspoken economics with warm close.",
      },
      {
        k: "Landing · Starter Set page",
        v: "Approved claim usage and visual treatment reference.",
      },
    ],
  },
];

export interface PerfHeadline {
  label: string;
  value: string;
  delta: string;
}

export const PERF_BIG: PerfHeadline[] = [
  { label: "Reach", value: "412k", delta: "+22% vs prior" },
  { label: "Engaged CTR", value: "2.4%", delta: "+0.3pts" },
  { label: "New subscriptions", value: "486", delta: "+14%" },
  { label: "CAC", value: "$18.20", delta: "−8%" },
];

export interface PerfWhy {
  title: string;
  body: string;
  link1: string;
  link2: string;
}

export const PERF_WHY: PerfWhy[] = [
  {
    title: "Demo-video format drives the CTR gain",
    body: "The 3 reels using math-on-screen pacing hold 3.1× the CTR of static posts with the same message.",
    link1: "Refill Launch",
    link2: "Instagram",
  },
  {
    title: "Economics framing lifts email",
    body: "Subject lines leading with cost beat sustainability framing by 9pts open rate across 8,400 sends.",
    link1: "Assumption: price-first",
    link2: "Email",
  },
  {
    title: "Mid-month dip traces to format, not message",
    body: "Engagement fell the week static posts replaced video — audience and copy were unchanged.",
    link1: "Refill Launch",
    link2: "Low-waste households",
  },
];

export interface PerfItem {
  title: string;
  body: string;
}

export const PERF_CHANGE: PerfItem[] = [
  {
    title: "Shift 2 remaining static posts to demo-video",
    body: "Affects Summer Refill Drop, weeks 4–5. Est. +18k reach at flat spend.",
  },
  {
    title: "Rebalance email split toward economics framing",
    body: "70/30 in favor of cost-led subject lines for the July newsletter.",
  },
  {
    title: "Add efficacy proof earlier for Skeptics",
    body: "Move the lab-test carousel ahead of the design story in the consideration sequence.",
  },
];

export const PERF_KEEP: PerfItem[] = [
  {
    title: "Positioning & pillars",
    body: "All three pillars performing at or above target — no change.",
  },
  {
    title: "Channel mix",
    body: "Instagram + email split validated; YouTube test stays small until cutdown data lands.",
  },
];

export interface CampaignRow {
  slug: string;
  name: string;
  objective: string;
  stage: string;
  stageNum: string;
  status: Status;
  next: string;
  updated: string;
}

/**
 * Returns the fixture campaign portfolio, reflecting the approve flag.
 *
 * Args:
 *   approved: Whether the Fernway Strategy stage has been approved.
 *
 * Returns:
 *   The campaign rows exactly as defined by the design prototype.
 */
export function campaignRows(approved: boolean): CampaignRow[] {
  return [
    {
      slug: "fernway-refill-launch",
      name: "Fernway Refill Launch",
      objective: "Acquisition · Q3 hero",
      stage: approved ? "Plan" : "Strategy",
      stageNum: approved ? "4/8" : "3/8",
      status: approved ? "In progress" : "Ready for review",
      next: approved
        ? "Channel strategy draft — today 4pm"
        : "Approve audience & positioning",
      updated: "2h ago",
    },
    {
      slug: "summer-refill-drop",
      name: "Summer Refill Drop",
      objective: "Seasonal promo",
      stage: "Produce",
      stageNum: "5/8",
      status: "In progress",
      next: "3 assets ready for review Thu",
      updated: "4h ago",
    },
    {
      slug: "loyalty-newsletter",
      name: "Loyalty Newsletter",
      objective: "Retention · monthly",
      stage: "Publish",
      stageNum: "7/8",
      status: "Ready for review",
      next: "Approve publishing schedule",
      updated: "1d ago",
    },
    {
      slug: "earth-month-retargeting",
      name: "Earth Month Retargeting",
      objective: "Re-engagement",
      stage: "Plan",
      stageNum: "4/8",
      status: "Needs input",
      next: "Confirm budget split",
      updated: "2d ago",
    },
  ];
}

export const FIXTURE_CAMPAIGN_SLUGS = campaignRows(false).map(
  (row) => row.slug,
);

/**
 * Resolves a fixture campaign's display name to its workspace slug.
 *
 * Args:
 *   name: A campaign display name.
 *
 * Returns:
 *   The workspace route slug, or null when the name is unknown.
 */
export function campaignSlugForName(name: string): string | null {
  const row = campaignRows(false).find((campaign) => campaign.name === name);
  return row ? row.slug : null;
}

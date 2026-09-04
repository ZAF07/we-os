import type { Status } from "@/lib/status";

/** The campaign the Home and Calendar fixtures still point at. */
const WORKSPACE_SLUG = "fernway-refill-launch";

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

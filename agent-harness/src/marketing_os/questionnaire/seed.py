"""The question set a fresh deployment starts with, and the DNA sections it fills.

Version 1 of the admin-curated questionnaire. It ships in code so a deployment
with an empty database still has a usable onboarding, and it is the *seed* only:
the admin publishes later versions into the questionnaire store without a deploy
(ADR-0018).

Every question asks for a fact the business owner uniquely knows. The crafted
artifacts — positioning, value proposition, messaging, brand voice as written,
channel selection — are deliberately absent: the engine produces those and the
owner approves them at the stage gates. That division is checked by a test, so
adding such a question here fails the suite rather than reaching a business.

The ``field`` and ``section`` on each question are the Brand DNA labels from
``templates/brand-dna.md``, which is what makes the rendered markdown the same
document the specialists already read.
"""

from __future__ import annotations

from marketing_os.schemas import Question, Questionnaire

SEED_VERSION = 1
SEED_PUBLISHED_AT = "2026-09-01T00:00:00Z"

BUSINESS = "Business"
CUSTOMERS = "Customers"
DIFFERENTIATION = "Differentiation"
REACH_AND_CONSTRAINTS = "Reach & constraints"
RECOMMENDED = "Recommended"

SECTION_ORDER = (BUSINESS, CUSTOMERS, DIFFERENTIATION, REACH_AND_CONSTRAINTS, RECOMMENDED)

SEED_QUESTIONS = [
    Question(
        id="q_business_name",
        field="Business name",
        section=BUSINESS,
        text="What is your business called?",
        why_we_ask="Every recommendation is grounded in your business, starting with its name.",
        help_text="Use the name your customers know you by, not the registered entity.",
        input_type="text",
        required=True,
    ),
    Question(
        id="q_what_they_sell",
        field="What they sell",
        section=BUSINESS,
        text="What do you sell?",
        why_we_ask="Concrete products and services are what a campaign can actually promote.",
        help_text="List them one per line, in the words you use with customers.",
        input_type="textarea",
        required=True,
    ),
    Question(
        id="q_category",
        field="Category / industry",
        section=BUSINESS,
        text="What category or industry are you in?",
        why_we_ask="The category sets which competitors and buying habits research looks at.",
        help_text='For example "boutique fitness", "B2B SaaS", "family restaurant".',
        input_type="text",
        required=True,
    ),
    Question(
        id="q_price_point",
        field="Price point",
        section=BUSINESS,
        text="What do your main products or services cost?",
        why_we_ask="Positioning and channel choices differ sharply for premium and value offers.",
        help_text='Rough ranges are fine, for example "$6–9 per drink" or "$90/month".',
        input_type="text",
        required=True,
    ),
    Question(
        id="q_segments",
        field="Primary segment(s)",
        section=CUSTOMERS,
        text="Who buys from you? Describe each distinct group, most important first.",
        why_we_ask="A campaign targets one specific group of buyers, never everyone.",
        help_text="Two to four groups, one per line, with what defines each.",
        input_type="list",
        required=True,
    ),
    Question(
        id="q_pain_points",
        field="Pain points / jobs-to-be-done",
        section=CUSTOMERS,
        text="What problems do those buyers hire you to solve?",
        why_we_ask="Messaging that names a real problem outperforms messaging about you.",
        help_text="Say it the way a customer would say it, not in marketing language.",
        input_type="textarea",
        required=True,
    ),
    Question(
        id="q_why_chosen",
        field="Why customers choose them over alternatives",
        section=DIFFERENTIATION,
        text="When a customer picks you over an alternative, what decided it?",
        why_we_ask="The honest reason is the raw material we build your positioning from.",
        help_text='Be specific and true — "great quality" tells us nothing usable.',
        input_type="textarea",
        required=True,
    ),
    Question(
        id="q_geography",
        field="Geography / service area",
        section=REACH_AND_CONSTRAINTS,
        text="Where do you serve customers?",
        why_we_ask="Targeting and budget both depend on how much ground a campaign covers.",
        help_text='Cities, a radius, regions — or "online only".',
        input_type="text",
        required=True,
    ),
    Question(
        id="q_languages",
        field="Language(s)",
        section=REACH_AND_CONSTRAINTS,
        text="What languages do your customers speak?",
        why_we_ask="Every asset has to be written in a language your buyers actually read.",
        help_text="List each language you want work produced in.",
        input_type="text",
        required=True,
    ),
    Question(
        id="q_budget_range",
        field="Budget range",
        section=REACH_AND_CONSTRAINTS,
        text="What can you spend on marketing in a typical month?",
        why_we_ask="A plan you cannot fund is not a plan; the budget bounds what we recommend.",
        help_text="A range is fine. Include ad spend and anything you pay suppliers.",
        input_type="currency",
        required=True,
    ),
    Question(
        id="q_hard_constraints",
        field="Hard constraints",
        section=REACH_AND_CONSTRAINTS,
        text="What must never appear in your marketing?",
        why_we_ask="Legal limits and off-limits topics are yours to set, and we enforce them.",
        help_text="Regulated claims, topics to avoid, anything compliance forbids.",
        input_type="textarea",
        required=True,
    ),
    Question(
        id="q_competitors",
        field="Competitors",
        section=RECOMMENDED,
        text="Who do you lose deals to?",
        why_we_ask="Naming real competitors makes the research specific instead of generic.",
        help_text="One per line. Their name is enough; add how they sell if you know.",
        input_type="textarea",
        required=False,
    ),
    Question(
        id="q_current_channels",
        field="Current channels & results",
        section=RECOMMENDED,
        text="Where do you market today, and what has worked or failed?",
        why_we_ask="What you have already tried stops us recommending it again blindly.",
        help_text="Include the failures — they are the more useful half.",
        input_type="textarea",
        required=False,
    ),
    Question(
        id="q_proof_points",
        field="Proof points",
        section=RECOMMENDED,
        text="What proof do you have that you deliver?",
        why_we_ask="Every claim we publish has to be backed by something real.",
        help_text="Testimonials, results, awards, data, credentials.",
        input_type="textarea",
        required=False,
    ),
    Question(
        id="q_objections",
        field="Common objections",
        section=RECOMMENDED,
        text="Why do prospects hesitate or say no?",
        why_we_ask="Answering the real objection is usually what turns interest into a sale.",
        help_text="The reasons you hear most often, in their words.",
        input_type="textarea",
        required=False,
    ),
    Question(
        id="q_baseline_metrics",
        field="Baseline metrics",
        section=RECOMMENDED,
        text="What are your current numbers?",
        why_we_ask="Without a baseline we cannot tell you whether a campaign worked.",
        help_text="Conversion rate, cost per acquisition, traffic, bookings a month.",
        input_type="textarea",
        required=False,
    ),
]

SEED_QUESTIONNAIRE = Questionnaire(
    version=SEED_VERSION,
    published_at=SEED_PUBLISHED_AT,
    questions=SEED_QUESTIONS,
)

"""Seed the end-to-end suite's tenant, so specs assert on known values.

The suite needs a business whose Brand DNA is *fixed*: a spec that picks
"whatever the first radio happens to be" asserts nothing about the system. That
is what this writes.

The wrinkle it exists to solve: a tenant id is ``ten_<uuid4>`` — random, minted
on a business's first authenticated request (ADR-0014) — so it cannot be derived
from a Clerk organization id, and a seed cannot know in advance which tenant to
write to. So this inserts the ``tenants`` row *itself*, pairing a known
``tenant_id`` with the Clerk organization the test user belongs to. When that
user signs in, :meth:`PostgresTenantDirectory.resolve` finds this row instead of
minting a fresh one, and the DNA seeded here is already theirs.

Idempotent: re-running it leaves the same tenant with the same answers, so the
compose stack can seed on every start without accumulating state.
"""

from __future__ import annotations

import argparse
import sys

from marketing_os.questionnaire import SEED_QUESTIONNAIRE, render_brand_dna
from marketing_os.schemas import BrandDnaRecord, DnaAnswer

TEST_TENANT_ID = "ten_e2e0000000000000000000000000000"
"""The fixed tenant id the suite's business owns.

Written rather than minted, which is the whole point: a random id could not be
referred to by a seed, a spec, or a person debugging a failure.
"""

TEST_BUSINESS_NAME = "Summit Climbing Collective"

SEGMENT_NAMES = [
    "Urban 22-35 beginners curious about climbing",
    "Weekend boulderers plateauing at V4",
]
"""The Audience Segments a spec may assert on by name.

A campaign targets exactly one segment, and the wizard offers exactly what the
Brand DNA names — so these strings are the contract between the seed and any
spec that picks a segment.
"""

ANSWERS: dict[str, str] = {
    "q_business_name": TEST_BUSINESS_NAME,
    "q_what_they_sell": ("Indoor climbing gym memberships, beginner courses, and coaching blocks."),
    "q_category": "Fitness and recreation",
    "q_price_point": "SGD 138/month membership; SGD 90 for a four-week beginner course",
    "q_segments": "\n".join(SEGMENT_NAMES),
    "q_pain_points": (
        "Beginners find climbing gyms intimidating and do not know what a first "
        "session involves. Plateaued climbers stop improving and drift away."
    ),
    "q_why_chosen": (
        "Coaching is included rather than sold separately, and every new member "
        "gets a first session walked through by a coach."
    ),
    "q_geography": "Singapore",
    "q_languages": "English",
    "q_budget_range": "SGD 4000 per campaign",
    "q_hard_constraints": (
        "No claims about injury prevention. No imagery of unroped climbing at height."
    ),
}
"""A complete answer to every Required question, so the DNA Gate passes.

An incomplete Brand DNA halts every campaign at Stage 0, which would make the
suite test the gate rather than the screens it is aiming at.
"""


def _rendered_dna(version: int) -> str:
    """Render the Brand DNA markdown the gate and the segment parser read.

    Args:
        version: The questionnaire version the answers were given against.

    Returns:
        The markdown projection of :data:`ANSWERS`.
    """
    record = BrandDnaRecord(
        questionnaire_version=version,
        answers=[
            DnaAnswer(question_id=question_id, answer=answer)
            for question_id, answer in ANSWERS.items()
        ],
    )
    return render_brand_dna(SEED_QUESTIONNAIRE, record, business_name=TEST_BUSINESS_NAME)


def seed(dsn: str, organization_id: str) -> None:
    """Write the test tenant and its Brand DNA answers.

    Args:
        dsn: An administrative Postgres connection string.
        organization_id: The Clerk organization id the test user belongs to,
            which is what pairs this tenant to the person signing in.

    Raises:
        SystemExit: If the organization id is missing, since a tenant paired to
            nothing would never be found by the sign-in it exists to serve.
    """
    if not organization_id.strip():
        raise SystemExit(
            "No organization id. Set E2E_CLERK_ORG_ID to the Clerk organization "
            "your test user belongs to — see web/.env.local.example."
        )

    import psycopg

    version = SEED_QUESTIONNAIRE.version
    with psycopg.connect(dsn, autocommit=True) as connection:
        connection.execute(
            """
            INSERT INTO tenants (tenant_id, name, external_auth_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (external_auth_id)
            DO UPDATE SET tenant_id = EXCLUDED.tenant_id, name = EXCLUDED.name
            """,
            (TEST_TENANT_ID, TEST_BUSINESS_NAME, organization_id.strip()),
        )
        for question_id, answer in ANSWERS.items():
            connection.execute(
                """
                INSERT INTO dna_answers
                    (tenant_id, question_id, answer, questionnaire_version)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (tenant_id, question_id)
                DO UPDATE SET answer = EXCLUDED.answer,
                              questionnaire_version = EXCLUDED.questionnaire_version
                """,
                (TEST_TENANT_ID, question_id, answer, version),
            )

        # The answers are the source of truth, but the *markdown projection* is
        # what the gate reads and what `/brand-dna/segments` parses the Audience
        # Segments out of (ADR-0018). Saving through the API renders it as a side
        # effect; seeding straight into the tables has to do it explicitly, or
        # the business ends up with a complete DNA that names no segments and no
        # campaign can be created.
        connection.execute(
            """
            INSERT INTO documents (tenant_id, path, content)
            VALUES (%s, %s, %s)
            ON CONFLICT (tenant_id, path) DO UPDATE SET content = EXCLUDED.content
            """,
            (TEST_TENANT_ID, "dna.md", _rendered_dna(version)),
        )

    print(
        f"Seeded {TEST_BUSINESS_NAME} as {TEST_TENANT_ID}, "
        f"paired to {organization_id.strip()}, with {len(ANSWERS)} answers.",
        file=sys.stderr,
    )


def main() -> None:
    """Parse arguments and seed the tenant."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dsn", required=True, help="Administrative Postgres DSN.")
    parser.add_argument(
        "--organization-id",
        required=True,
        help="The Clerk organization id the test user belongs to.",
    )
    arguments = parser.parse_args()
    seed(arguments.dsn, arguments.organization_id)


if __name__ == "__main__":
    main()

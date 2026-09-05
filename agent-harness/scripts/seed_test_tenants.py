"""Seed the end-to-end suite's two tenants, so specs assert on known values.

The suite needs two businesses, and needs them to be a matched pair:

- **The seeded tenant** has a *fixed* Brand DNA, because a spec that picks
  "whatever the first radio happens to be" asserts nothing about the system, and
  because every campaign spec needs a business that passes the Stage 0 gate.
- **The blank tenant** has *no* Brand DNA, because the onboarding specs assert on
  the wizard's required-field gating and on the walk to the Brand screen —
  neither of which can fire against a business that has already answered.

The wrinkle it exists to solve: a tenant id is ``ten_<uuid4>`` — random, minted
on a business's first authenticated request (ADR-0014) — so it cannot be derived
from a Clerk organization id, and a seed cannot know in advance which tenant to
write to. So this inserts the ``tenants`` rows *itself*, pairing a known
``tenant_id`` with the Clerk organization each test user belongs to. When such a
user signs in, :meth:`PostgresTenantDirectory.resolve` finds this row instead of
minting a fresh one, and the state seeded here is already theirs.

Both tenants are written by one invocation, with no ``--blank`` or
``--tenant-id`` switch to call it twice: the pair is what the suite needs, and a
half-seeded stack should be unrepresentable.

Idempotent in the sense the suite needs — it *establishes fixture state* rather
than merely adding to it, which is a stronger and more useful claim than "adds
nothing twice". Re-running leaves the seeded tenant with the same answers,
re-blanks the blank tenant (the spec that completes the wizard fills it in), and
purges both tenants' campaigns (every spec that creates one leaves it behind).
So a suite run against a freshly started stack always sees the same fixture,
however many runs came before it.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from marketing_os.questionnaire import SEED_QUESTIONNAIRE, render_brand_dna
from marketing_os.schemas import BrandDnaRecord, DnaAnswer

TEST_TENANT_ID = "ten_e2e0000000000000000000000000000"
"""The fixed tenant id the suite's business owns.

Written rather than minted, which is the whole point: a random id could not be
referred to by a seed, a spec, or a person debugging a failure.
"""

TEST_BUSINESS_NAME = "Summit Climbing Collective"

BLANK_TENANT_ID = "ten_e2eblank000000000000000000000"
"""The fixed tenant id of the business that has answered nothing.

Seeded explicitly rather than left to :meth:`PostgresTenantDirectory.resolve`'s
auto-provisioning. Auto-provisioning does produce a blank tenant, but with a
random id nothing can name — and it does not exist until someone signs in, so
there would be no reliable moment at which to blank it again.
"""

BLANK_BUSINESS_NAME = "Blank Slate Testing"
"""The organization name the blank tenant is seeded under.

Deliberately *not* the name the onboarding spec answers with. The spec answers
``q_business_name`` as something else and asserts the Brand screen shows it,
which only proves the answer won over the organization name
(``questionnaire/render.py``) if the two differ.
"""

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


def _require_organization_id(organization_id: str, variable: str) -> str:
    """Return a Clerk organization id, refusing an empty one.

    Args:
        organization_id: The value read from the environment.
        variable: The environment variable it came from, named in the error so
            an operator knows which one to set.

    Returns:
        The organization id, stripped of surrounding whitespace.

    Raises:
        SystemExit: If the organization id is missing, since a tenant paired to
            nothing would never be found by the sign-in it exists to serve.
    """
    if not organization_id.strip():
        raise SystemExit(
            f"No organization id. Set {variable} to the Clerk organization "
            "your test user belongs to — see web/.env.local.example."
        )
    return organization_id.strip()


def _purge_campaigns(connection: Any, tenant_id: str) -> None:
    """Delete every campaign a tenant owns, and everything a campaign owns.

    Specs create campaigns and leave them behind, so without this the test
    tenants' campaign lists grow on every ``make test-e2e`` — and a spec
    asserting on a campaign *name* rather than a slug becomes a strict-mode
    violation the second time it runs, having passed the first.

    Five things are deleted, because a campaign owns rows in five places: its
    documents, the runs that produced them, the deliverable version chain, the
    usage it was charged for, and the LangGraph checkpoint threads a resumable
    run wrote. Leaving any behind orphans it — a checkpoint thread in
    particular, since a new campaign given the same slug would *resume* the old
    one's state.

    Scoped by tenant deliberately: this seed is pointed at a disposable stack,
    but a delete that swept every campaign in the database would be a footgun
    the first time someone pointed it somewhere else. Documents are scoped by
    path too, so ``dna.md`` survives — deleting the Brand DNA would halt every
    campaign spec at the Stage 0 gate.

    Args:
        connection: An open psycopg connection with administrative rights.
        tenant_id: The tenant whose campaigns are purged.
    """
    connection.execute(
        "DELETE FROM documents WHERE tenant_id = %s AND path LIKE 'campaigns/%%'",
        (tenant_id,),
    )
    connection.execute("DELETE FROM runs WHERE tenant_id = %s", (tenant_id,))
    connection.execute("DELETE FROM deliverable_versions WHERE tenant_id = %s", (tenant_id,))
    connection.execute("DELETE FROM usage_ledger WHERE tenant_id = %s", (tenant_id,))
    # Thread ids are `<tenant>/<slug>` and `<tenant>/<slug>:<stage>`
    # (`graph/checkpoints.py`), so one prefix covers every thread the tenant's
    # campaigns can have written under, including stages this seed cannot name.
    for table in ("checkpoint_writes", "checkpoint_blobs", "checkpoints"):
        connection.execute(
            f"DELETE FROM {table} WHERE thread_id LIKE %s",
            (f"{tenant_id}/%",),
        )


def _upsert_tenant(connection: Any, tenant_id: str, name: str, organization_id: str) -> None:
    """Write the ``tenants`` row pairing a fixed tenant id to a Clerk organization.

    Args:
        connection: An open psycopg connection with administrative rights.
        tenant_id: The fixed tenant id to write.
        name: The business name to record.
        organization_id: The Clerk organization id the test user belongs to.
    """
    connection.execute(
        """
        INSERT INTO tenants (tenant_id, name, external_auth_id)
        VALUES (%s, %s, %s)
        ON CONFLICT (external_auth_id)
        DO UPDATE SET tenant_id = EXCLUDED.tenant_id, name = EXCLUDED.name
        """,
        (tenant_id, name, organization_id),
    )


def seed_complete_tenant(dsn: str, organization_id: str) -> None:
    """Write the test tenant and its complete Brand DNA, and purge its campaigns.

    The purge is what keeps the tenant's campaign list the same length on every
    run — see :func:`_purge_campaigns`. The Brand DNA is rewritten rather than
    deleted, because every campaign spec needs a business that passes the DNA
    Gate.

    Args:
        dsn: An administrative Postgres connection string.
        organization_id: The Clerk organization id the test user belongs to,
            which is what pairs this tenant to the person signing in.
    """
    import psycopg

    version = SEED_QUESTIONNAIRE.version
    with psycopg.connect(dsn, autocommit=True) as connection:
        _upsert_tenant(connection, TEST_TENANT_ID, TEST_BUSINESS_NAME, organization_id)
        _purge_campaigns(connection, TEST_TENANT_ID)
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
        f"paired to {organization_id}, with {len(ANSWERS)} answers.",
        file=sys.stderr,
    )


def seed_blank_tenant(dsn: str, organization_id: str) -> None:
    """Write the blank tenant, purge its campaigns, and delete its Brand DNA.

    The delete is the point. The onboarding spec that walks the wizard leaves
    this tenant with a complete DNA, so blankness has to be re-established on
    every stack start rather than established once. Two things are deleted, not
    one: the wizard's resume point is computed from ``dna_answers``, but the DNA
    Gate and the segment parser read the rendered ``dna.md`` document
    (ADR-0018) — clearing only the answers would leave a tenant whose wizard
    looks empty and whose gate passes.

    Args:
        dsn: An administrative Postgres connection string.
        organization_id: The Clerk organization id the blank test user belongs
            to, which is what pairs this tenant to the person signing in.
    """
    import psycopg

    with psycopg.connect(dsn, autocommit=True) as connection:
        _upsert_tenant(connection, BLANK_TENANT_ID, BLANK_BUSINESS_NAME, organization_id)
        _purge_campaigns(connection, BLANK_TENANT_ID)
        connection.execute("DELETE FROM dna_answers WHERE tenant_id = %s", (BLANK_TENANT_ID,))
        connection.execute(
            "DELETE FROM documents WHERE tenant_id = %s AND path = %s",
            (BLANK_TENANT_ID, "dna.md"),
        )

    print(
        f"Blanked {BLANK_BUSINESS_NAME} as {BLANK_TENANT_ID}, paired to {organization_id}.",
        file=sys.stderr,
    )


def seed_all(dsn: str, organization_id: str, blank_organization_id: str) -> None:
    """Establish both tenants' fixture state in one pass.

    Args:
        dsn: An administrative Postgres connection string.
        organization_id: The Clerk organization the seeded test user belongs to.
        blank_organization_id: The Clerk organization the blank test user
            belongs to.

    Raises:
        SystemExit: If either organization id is missing, or if the two are the
            same — ``external_auth_id`` is unique, so one id would make the
            second tenant steal the first's pairing and the suite would run both
            Playwright projects against one tenant.
    """
    seeded = _require_organization_id(organization_id, "E2E_CLERK_ORG_ID")
    blank = _require_organization_id(blank_organization_id, "E2E_CLERK_BLANK_ORG_ID")
    if seeded == blank:
        raise SystemExit(
            "E2E_CLERK_ORG_ID and E2E_CLERK_BLANK_ORG_ID name the same Clerk "
            "organization. They must be two organizations, or the blank tenant "
            "takes over the seeded one's pairing and every spec sees one tenant."
        )

    seed_complete_tenant(dsn, seeded)
    seed_blank_tenant(dsn, blank)


def main() -> None:
    """Parse arguments and seed both tenants."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dsn", required=True, help="Administrative Postgres DSN.")
    parser.add_argument(
        "--organization-id",
        required=True,
        help="The Clerk organization id the seeded test user belongs to.",
    )
    parser.add_argument(
        "--blank-organization-id",
        required=True,
        help="The Clerk organization id the blank test user belongs to.",
    )
    arguments = parser.parse_args()
    seed_all(arguments.dsn, arguments.organization_id, arguments.blank_organization_id)


if __name__ == "__main__":
    main()

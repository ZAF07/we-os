"""What the e2e seed must guarantee about the fixture state it establishes.

The browser suite's two test tenants are a matched pair: one carries a complete
Brand DNA so campaign specs can reach the pipeline, the other carries none so
the onboarding specs can exercise the gate. Both claims are only true if the
seed *re-establishes* them on every stack start — the blank tenant is filled in
by the spec that walks the wizard, and the seeded tenant accumulates campaigns.

Marked ``slow`` like the rest of the Postgres suite: these assert on what the
seed leaves in real tables, which no fake can honestly model.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import seed_test_tenants  # noqa: E402

pytestmark = pytest.mark.slow

ORG_ID = "org_e2e_seeded"
BLANK_ORG_ID = "org_e2e_blank"


@pytest.fixture
def empty_database(postgres_dsn: str, postgres_superuser_dsn: str) -> str:
    """Truncate every harness table and return the admin connection string.

    The seed connects administratively, as it does in compose — it writes the
    ``tenants`` row, which the application role has no business creating.

    Args:
        postgres_dsn: The application role's connection string, depended on so
            the schema exists before anything queries it.
        postgres_superuser_dsn: The container's admin connection string.

    Returns:
        The admin connection string, with every harness table emptied.
    """
    import psycopg
    from langgraph.checkpoint.postgres import PostgresSaver

    from marketing_os.adapters.postgres.schema import TABLES

    # The seed purges checkpoint threads, which live in the checkpointer's own
    # tables. Compose creates them before the seed runs — `init-db` calls the
    # same `setup()` — so the fixture does too, rather than making the seed
    # defensive about a table its caller guarantees.
    with PostgresSaver.from_conn_string(postgres_superuser_dsn) as saver:
        saver.setup()
    with psycopg.connect(postgres_superuser_dsn, autocommit=True) as connection:
        connection.execute(f"TRUNCATE {', '.join(TABLES)}")
        connection.execute("TRUNCATE checkpoints, checkpoint_blobs, checkpoint_writes")
    return postgres_superuser_dsn


def _fetch(dsn: str, sql: str, parameters: tuple[Any, ...]) -> list[tuple[Any, ...]]:
    """Run a query as the superuser and return its rows.

    Args:
        dsn: An administrative connection string.
        sql: The query to run.
        parameters: The query's bound parameters.

    Returns:
        Every row the query returned.
    """
    import psycopg

    with psycopg.connect(dsn, autocommit=True) as connection:
        return list(connection.execute(sql, parameters).fetchall())


def test_seeding_writes_both_tenants(empty_database: str) -> None:
    seed_test_tenants.seed_all(empty_database, ORG_ID, BLANK_ORG_ID)

    rows = _fetch(
        empty_database,
        "SELECT tenant_id, external_auth_id FROM tenants ORDER BY tenant_id",
        (),
    )
    assert dict(rows) == {
        seed_test_tenants.TEST_TENANT_ID: ORG_ID,
        seed_test_tenants.BLANK_TENANT_ID: BLANK_ORG_ID,
    }


def test_the_seeded_tenant_gets_a_complete_dna(empty_database: str) -> None:
    seed_test_tenants.seed_all(empty_database, ORG_ID, BLANK_ORG_ID)

    answers = _fetch(
        empty_database,
        "SELECT count(*) FROM dna_answers WHERE tenant_id = %s",
        (seed_test_tenants.TEST_TENANT_ID,),
    )
    documents = _fetch(
        empty_database,
        "SELECT content FROM documents WHERE tenant_id = %s AND path = 'dna.md'",
        (seed_test_tenants.TEST_TENANT_ID,),
    )
    assert answers[0][0] == len(seed_test_tenants.ANSWERS)
    assert seed_test_tenants.SEGMENT_NAMES[0] in documents[0][0]


def test_the_blank_tenant_starts_with_no_dna(empty_database: str) -> None:
    seed_test_tenants.seed_all(empty_database, ORG_ID, BLANK_ORG_ID)

    answers = _fetch(
        empty_database,
        "SELECT count(*) FROM dna_answers WHERE tenant_id = %s",
        (seed_test_tenants.BLANK_TENANT_ID,),
    )
    documents = _fetch(
        empty_database,
        "SELECT count(*) FROM documents WHERE tenant_id = %s AND path = 'dna.md'",
        (seed_test_tenants.BLANK_TENANT_ID,),
    )
    assert answers[0][0] == 0
    assert documents[0][0] == 0


def test_reseeding_blanks_a_tenant_the_wizard_filled_in(empty_database: str) -> None:
    """The onboarding spec that completes the wizard leaves the blank tenant full.

    Blankness therefore has to be re-established, not merely established once —
    otherwise the second run of the suite tests a tenant the first run dirtied.
    """
    import psycopg

    seed_test_tenants.seed_all(empty_database, ORG_ID, BLANK_ORG_ID)
    with psycopg.connect(empty_database, autocommit=True) as connection:
        connection.execute(
            "INSERT INTO dna_answers (tenant_id, question_id, answer, questionnaire_version) "
            "VALUES (%s, 'q_business_name', 'Acme Coffee', 1)",
            (seed_test_tenants.BLANK_TENANT_ID,),
        )
        connection.execute(
            "INSERT INTO documents (tenant_id, path, content) VALUES (%s, 'dna.md', '# Acme')",
            (seed_test_tenants.BLANK_TENANT_ID,),
        )

    seed_test_tenants.seed_all(empty_database, ORG_ID, BLANK_ORG_ID)

    answers = _fetch(
        empty_database,
        "SELECT count(*) FROM dna_answers WHERE tenant_id = %s",
        (seed_test_tenants.BLANK_TENANT_ID,),
    )
    documents = _fetch(
        empty_database,
        "SELECT count(*) FROM documents WHERE tenant_id = %s AND path = 'dna.md'",
        (seed_test_tenants.BLANK_TENANT_ID,),
    )
    assert answers[0][0] == 0
    assert documents[0][0] == 0


def test_reseeding_keeps_the_seeded_tenants_dna(empty_database: str) -> None:
    seed_test_tenants.seed_all(empty_database, ORG_ID, BLANK_ORG_ID)
    seed_test_tenants.seed_all(empty_database, ORG_ID, BLANK_ORG_ID)

    answers = _fetch(
        empty_database,
        "SELECT count(*) FROM dna_answers WHERE tenant_id = %s",
        (seed_test_tenants.TEST_TENANT_ID,),
    )
    assert answers[0][0] == len(seed_test_tenants.ANSWERS)


def test_a_missing_organization_id_is_refused(empty_database: str) -> None:
    with pytest.raises(SystemExit):
        seed_test_tenants.seed_all(empty_database, "  ", BLANK_ORG_ID)


def test_a_missing_blank_organization_id_is_refused(empty_database: str) -> None:
    with pytest.raises(SystemExit):
        seed_test_tenants.seed_all(empty_database, ORG_ID, "")


def test_the_two_tenants_are_distinct() -> None:
    """A shared org id would pair both tenant rows to one business.

    ``external_auth_id`` is unique, so the second insert would steal the first
    tenant's pairing and the suite would silently run both projects against one
    tenant.
    """
    assert seed_test_tenants.TEST_TENANT_ID != seed_test_tenants.BLANK_TENANT_ID
    assert seed_test_tenants.TEST_BUSINESS_NAME != seed_test_tenants.BLANK_BUSINESS_NAME


# --- Campaign purging -----------------------------------------------------------


def _make_campaign(dsn: str, tenant_id: str, slug: str) -> None:
    """Write everything a finished campaign leaves behind, for one campaign.

    Args:
        dsn: An administrative connection string.
        tenant_id: The tenant the campaign belongs to.
        slug: The campaign slug.
    """
    import psycopg

    with psycopg.connect(dsn, autocommit=True) as connection:
        connection.execute(
            "INSERT INTO documents (tenant_id, path, content) VALUES (%s, %s, 'goal')",
            (tenant_id, f"campaigns/{slug}/goal.md"),
        )
        connection.execute(
            "INSERT INTO runs (run_id, tenant_id, user_id, slug, stage, status) "
            "VALUES (%s, %s, 'u_1', %s, 'research', 'completed')",
            (f"run_{tenant_id}_{slug}", tenant_id, slug),
        )
        connection.execute(
            "INSERT INTO deliverable_versions "
            "(tenant_id, slug, stage_key, version, content) VALUES (%s, %s, 'research', 1, 'x')",
            (tenant_id, slug),
        )
        connection.execute(
            "INSERT INTO usage_ledger (tenant_id, slug, stage_key, kind, model, units, cost) "
            "VALUES (%s, %s, 'research', 'model', 'scripted', 10, 0.01)",
            (tenant_id, slug),
        )
        connection.execute(
            "INSERT INTO checkpoints "
            "(thread_id, checkpoint_ns, checkpoint_id, checkpoint, metadata) "
            "VALUES (%s, '', 'cp_1', '{}'::jsonb, '{}'::jsonb)",
            (f"{tenant_id}/{slug}",),
        )


def _campaign_row_counts(dsn: str, tenant_id: str) -> dict[str, int]:
    """Count everything a tenant's campaigns own, table by table.

    Args:
        dsn: An administrative connection string.
        tenant_id: The tenant to count for.

    Returns:
        Row counts keyed by what they count, so a purge can be asserted to have
        left nothing orphaned in any of them.
    """
    return {
        "documents": _fetch(
            dsn,
            "SELECT count(*) FROM documents WHERE tenant_id = %s AND path LIKE 'campaigns/%%'",
            (tenant_id,),
        )[0][0],
        "runs": _fetch(dsn, "SELECT count(*) FROM runs WHERE tenant_id = %s", (tenant_id,))[0][0],
        "deliverable_versions": _fetch(
            dsn,
            "SELECT count(*) FROM deliverable_versions WHERE tenant_id = %s",
            (tenant_id,),
        )[0][0],
        "usage_ledger": _fetch(
            dsn, "SELECT count(*) FROM usage_ledger WHERE tenant_id = %s", (tenant_id,)
        )[0][0],
        "checkpoints": _fetch(
            dsn,
            "SELECT count(*) FROM checkpoints WHERE thread_id LIKE %s",
            (f"{tenant_id}/%",),
        )[0][0],
    }


NOTHING_LEFT = {
    "documents": 0,
    "runs": 0,
    "deliverable_versions": 0,
    "usage_ledger": 0,
    "checkpoints": 0,
}
"""What a tenant owns once its campaigns have been purged: nothing, anywhere."""


def test_reseeding_purges_the_campaigns_a_run_left_behind(empty_database: str) -> None:
    """Every spec that creates a campaign leaves it behind, run after run.

    Without a purge the seeded tenant's campaign list grows on every
    ``make test-e2e``, and a spec asserting on a campaign *name* rather than a
    slug becomes a strict-mode violation on the second run.
    """
    seed_test_tenants.seed_all(empty_database, ORG_ID, BLANK_ORG_ID)
    _make_campaign(empty_database, seed_test_tenants.TEST_TENANT_ID, "spring-refill")
    _make_campaign(empty_database, seed_test_tenants.BLANK_TENANT_ID, "acme-launch")

    seed_test_tenants.seed_all(empty_database, ORG_ID, BLANK_ORG_ID)

    assert _campaign_row_counts(empty_database, seed_test_tenants.TEST_TENANT_ID) == NOTHING_LEFT
    assert _campaign_row_counts(empty_database, seed_test_tenants.BLANK_TENANT_ID) == NOTHING_LEFT


def test_purging_campaigns_leaves_the_seeded_dna_alone(empty_database: str) -> None:
    """The purge must take campaigns and stop there.

    ``dna.md`` is a document like any campaign document, so a purge that deleted
    by tenant rather than by path would take the Brand DNA with it and every
    campaign spec would halt at the Stage 0 gate.
    """
    seed_test_tenants.seed_all(empty_database, ORG_ID, BLANK_ORG_ID)
    _make_campaign(empty_database, seed_test_tenants.TEST_TENANT_ID, "spring-refill")

    seed_test_tenants.seed_all(empty_database, ORG_ID, BLANK_ORG_ID)

    documents = _fetch(
        empty_database,
        "SELECT count(*) FROM documents WHERE tenant_id = %s AND path = 'dna.md'",
        (seed_test_tenants.TEST_TENANT_ID,),
    )
    answers = _fetch(
        empty_database,
        "SELECT count(*) FROM dna_answers WHERE tenant_id = %s",
        (seed_test_tenants.TEST_TENANT_ID,),
    )
    assert documents[0][0] == 1
    assert answers[0][0] == len(seed_test_tenants.ANSWERS)


def test_purging_leaves_another_tenants_campaigns_alone(empty_database: str) -> None:
    """The purge is scoped to the two test tenants, not the whole database.

    A seed that swept every campaign in the database would be a footgun the
    moment anyone pointed it at something other than the disposable e2e stack.
    """
    import psycopg

    other = "ten_someone_else"
    seed_test_tenants.seed_all(empty_database, ORG_ID, BLANK_ORG_ID)
    with psycopg.connect(empty_database, autocommit=True) as connection:
        connection.execute(
            "INSERT INTO tenants (tenant_id, name, external_auth_id) VALUES (%s, %s, %s)",
            (other, "Someone Else", "org_someone_else"),
        )
    _make_campaign(empty_database, other, "their-campaign")

    seed_test_tenants.seed_all(empty_database, ORG_ID, BLANK_ORG_ID)

    assert _campaign_row_counts(empty_database, other) == {
        "documents": 1,
        "runs": 1,
        "deliverable_versions": 1,
        "usage_ledger": 1,
        "checkpoints": 1,
    }

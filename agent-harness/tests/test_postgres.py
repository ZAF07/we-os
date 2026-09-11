"""What only a real Postgres can prove, against a real containerised Postgres.

The document-store *contract* is covered by the shared conformance suite in
``test_documentstore.py``, which the Postgres adapter joins. This file covers
what an in-memory fake cannot honestly model, and which is therefore exactly
where the expensive bugs live:

- **Row-level security.** Tenant isolation is the highest-severity bug class in
  this work, and a dict cannot demonstrate that a query which *forgot* its
  tenant predicate still returns nothing across tenants.
- **The run claim as a database constraint.** "One campaign, one person at a
  time" only holds if Postgres refuses the second claim; a check-then-insert in
  Python would pass a single-threaded test and lose the race under two
  simultaneous requests.
- **A checkpointer that survives the process.** The whole reason Postgres is a
  hard prerequisite for approval gates.

Every test here is marked ``slow`` and skips unless
``MARKETING_OS_TEST_POSTGRES=1`` is set, so the fast suite needs no Docker.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from langgraph.types import Command

from conftest import (
    ASK_QUESTIONS,
    OTHER_TENANT,
    SLUG,
    TENANT,
    answered_clarifications,
    asking_handler,
    asking_until_answered_handler,
    install_scripted_graph,
    prototype_adapters,
    write_all_agent_specs,
)
from marketing_os.adapters.deliverables import InMemoryDeliverableStore
from marketing_os.adapters.observability import new_run_id
from marketing_os.adapters.postgres import (
    PostgresAnswerStore,
    PostgresDeliverableStore,
    PostgresDocumentStore,
    PostgresQuestionnaireStore,
    PostgresRunStore,
    PostgresTenantDirectory,
)
from marketing_os.adapters.postgres.schema import TENANT_SETTING
from marketing_os.adapters.runs import AWAITING_APPROVAL, AWAITING_CLARIFICATION
from marketing_os.config import Settings
from marketing_os.errors import (
    DocumentNotFoundError,
    RunConflictError,
    TierAlreadySetError,
    ToolError,
)
from marketing_os.graph.checkpoints import clear_campaign_threads, thread_id
from marketing_os.graph.runner import arun_campaign, awaiting_approval_stage, pending_hold
from marketing_os.questionnaire import CLARIFICATIONS_HEADING, SEED_QUESTIONNAIRE, render_brand_dna
from marketing_os.schemas import DnaAnswer, RunRecord

pytestmark = pytest.mark.slow


# --- Row-level security ---------------------------------------------------------


def test_a_query_with_no_tenant_scope_returns_nothing_across_tenants(
    postgres_pool: Any,
) -> None:
    """The backstop: forgetting the tenant predicate leaks nothing, it returns nothing.

    This is deliberately raw SQL with no ``WHERE tenant_id``, which is precisely
    the mistake new code makes. Under the policy it sees only the tenant the
    transaction was scoped to.
    """
    store = PostgresDocumentStore(postgres_pool)
    store.write(TENANT, "dna.md", "# Mine")
    store.write(OTHER_TENANT, "dna.md", "# Theirs")

    with postgres_pool.connection() as connection:
        connection.execute("SELECT set_config(%s, %s, true)", (TENANT_SETTING, TENANT))
        unscoped = connection.execute("SELECT tenant_id, content FROM documents").fetchall()

    assert [(row[0], row[1]) for row in unscoped] == [(TENANT, "# Mine")]


def test_a_transaction_with_no_tenant_set_sees_no_documents_at_all(
    postgres_pool: Any,
) -> None:
    """Failing closed matters more than failing loudly: unscoped means empty, never all."""
    PostgresDocumentStore(postgres_pool).write(TENANT, "dna.md", "# Mine")

    with postgres_pool.connection() as connection:
        rows = connection.execute("SELECT tenant_id FROM documents").fetchall()

    assert rows == []


def test_one_tenant_cannot_write_a_row_labelled_as_another(postgres_pool: Any) -> None:
    """The policy's ``WITH CHECK`` half — isolation covers writes, not only reads."""
    import psycopg

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with postgres_pool.connection() as connection:
            connection.execute("SELECT set_config(%s, %s, true)", (TENANT_SETTING, TENANT))
            connection.execute(
                "INSERT INTO documents (tenant_id, path, content) VALUES (%s, %s, %s)",
                (OTHER_TENANT, "dna.md", "# Smuggled"),
            )


def test_the_store_cannot_read_another_tenants_document(postgres_pool: Any) -> None:
    store = PostgresDocumentStore(postgres_pool)
    store.write(TENANT, "campaigns/spring/research.md", "# Mine")

    assert store.exists(OTHER_TENANT, "campaigns/spring/research.md") is False
    assert store.list(OTHER_TENANT, "campaigns/spring") == []


# --- The tenant directory -------------------------------------------------------


def test_the_clerk_organization_id_lives_in_a_column_not_in_the_tenant_id(
    postgres_pool: Any,
) -> None:
    """The pairing this table exists for: a platform id, a name, and the IdP's id."""
    directory = PostgresTenantDirectory(postgres_pool)

    tenant = directory.resolve(external_auth_id="org_3IlR", name="Coast Coffee")

    assert tenant.tenant_id.startswith("ten_")
    assert tenant.external_auth_id == "org_3IlR"
    assert directory.get(tenant.tenant_id) == tenant


def test_resolving_the_same_organization_twice_reuses_its_tenant(postgres_pool: Any) -> None:
    """Two workers seeing a business's first request must not mint two tenants."""
    directory = PostgresTenantDirectory(postgres_pool)

    first = directory.resolve(external_auth_id="org_3IlR", name="Coast Coffee")
    second = PostgresTenantDirectory(postgres_pool).resolve(
        external_auth_id="org_3IlR", name="Coast Coffee Roasters"
    )

    assert second.tenant_id == first.tenant_id
    assert second.name == "Coast Coffee Roasters"


def test_a_new_tenant_reports_no_tier(postgres_pool: Any) -> None:
    directory = PostgresTenantDirectory(postgres_pool)

    tenant = directory.resolve(external_auth_id="org_tierless", name="Coast Coffee")

    assert tenant.tier is None
    assert directory.get(tenant.tenant_id) == tenant


def test_a_tier_is_set_once_and_read_back_by_every_path(postgres_pool: Any) -> None:
    """The column is the platform's record of the tier (ADR-0027), not the IdP's."""
    directory = PostgresTenantDirectory(postgres_pool)
    tenant = directory.resolve(external_auth_id="org_tiered", name="Coast Coffee")

    recorded = directory.set_tier(tenant.tenant_id, "command")

    assert recorded.tier == "command"
    found = directory.get(tenant.tenant_id)
    assert found is not None and found.tier == "command"
    resolved = PostgresTenantDirectory(postgres_pool).resolve(
        external_auth_id="org_tiered", name="Coast Coffee Roasters"
    )
    assert resolved.tier == "command"
    assert resolved.name == "Coast Coffee Roasters"


def test_repeating_the_tier_is_harmless_and_changing_it_is_refused(postgres_pool: Any) -> None:
    directory = PostgresTenantDirectory(postgres_pool)
    tenant = directory.resolve(external_auth_id="org_set_once", name="Coast Coffee")
    directory.set_tier(tenant.tenant_id, "operator")

    assert directory.set_tier(tenant.tenant_id, "operator").tier == "operator"
    with pytest.raises(TierAlreadySetError):
        directory.set_tier(tenant.tenant_id, "strategist")
    found = directory.get(tenant.tenant_id)
    assert found is not None and found.tier == "operator"


def test_a_tier_cannot_be_set_for_a_tenant_that_does_not_exist(postgres_pool: Any) -> None:
    with pytest.raises(ToolError):
        PostgresTenantDirectory(postgres_pool).set_tier("ten_never_minted", "operator")


def test_a_new_tenant_has_never_reviewed_its_dna(postgres_pool: Any) -> None:
    directory = PostgresTenantDirectory(postgres_pool)

    tenant = directory.resolve(external_auth_id="org_unreviewed", name="Coast Coffee")

    assert tenant.dna_reviewed_at is None


def test_a_dna_review_is_recorded_and_read_back_by_every_path(postgres_pool: Any) -> None:
    """The column is the one timestamp the Review item and the reminder derive from (ADR-0028)."""
    directory = PostgresTenantDirectory(postgres_pool)
    tenant = directory.resolve(external_auth_id="org_reviewed", name="Coast Coffee")
    at = datetime(2026, 9, 11, 9, 0, tzinfo=UTC)

    marked = directory.mark_dna_reviewed(tenant.tenant_id, at=at)

    assert marked.dna_reviewed_at == at
    found = directory.get(tenant.tenant_id)
    assert found is not None and found.dna_reviewed_at == at
    resolved = directory.resolve(external_auth_id="org_reviewed", name="Coast Coffee Roasters")
    assert resolved.dna_reviewed_at == at
    later = directory.mark_dna_reviewed(tenant.tenant_id, at=at + timedelta(days=7))
    assert later.dna_reviewed_at == at + timedelta(days=7)


def test_a_review_cannot_be_recorded_for_a_tenant_that_does_not_exist(
    postgres_pool: Any,
) -> None:
    with pytest.raises(ToolError):
        PostgresTenantDirectory(postgres_pool).mark_dna_reviewed(
            "ten_missing", at=datetime.now(UTC)
        )


def test_the_signed_in_email_is_recorded_and_kept_when_a_later_request_has_none(
    postgres_pool: Any,
) -> None:
    """The reminder has no request to read an address from, so the row keeps the last one."""
    directory = PostgresTenantDirectory(postgres_pool)

    first = directory.resolve(external_auth_id="org_mailed", name="Coast Coffee")
    assert first.contact_email is None
    signed_in = directory.resolve(
        external_auth_id="org_mailed", name="Coast Coffee", email="sam@coastcoffee.example"
    )
    assert signed_in.contact_email == "sam@coastcoffee.example"
    later = directory.resolve(external_auth_id="org_mailed", name="Coast Coffee")
    assert later.contact_email == "sam@coastcoffee.example"
    colleague = directory.resolve(
        external_auth_id="org_mailed", name="Coast Coffee", email="ana@coastcoffee.example"
    )
    assert colleague.contact_email == "ana@coastcoffee.example"
    found = directory.get(first.tenant_id)
    assert found is not None and found.contact_email == "ana@coastcoffee.example"


def test_every_registered_tenant_is_listed_once(postgres_pool: Any) -> None:
    directory = PostgresTenantDirectory(postgres_pool)
    mine = directory.resolve(external_auth_id="org_listed_a", name="A")
    theirs = directory.resolve(external_auth_id="org_listed_b", name="B")
    directory.resolve(external_auth_id="org_listed_a", name="A renamed")

    listed = {tenant.tenant_id: tenant for tenant in directory.all()}

    assert {mine.tenant_id, theirs.tenant_id} <= set(listed)
    assert listed[mine.tenant_id].name == "A renamed"
    assert len(listed) == len(directory.all())


def test_a_reminder_is_recorded_and_read_back_by_every_path(postgres_pool: Any) -> None:
    directory = PostgresTenantDirectory(postgres_pool)
    tenant = directory.resolve(external_auth_id="org_reminded", name="Coast Coffee")
    at = datetime(2026, 9, 11, 9, 0, tzinfo=UTC)

    reminded = directory.mark_dna_reminded(tenant.tenant_id, at=at)

    assert reminded.dna_reminded_at == at
    found = directory.get(tenant.tenant_id)
    assert found is not None and found.dna_reminded_at == at
    assert directory.resolve(external_auth_id="org_reminded").dna_reminded_at == at
    listed = [t for t in directory.all() if t.tenant_id == tenant.tenant_id]
    assert listed[0].dna_reminded_at == at
    with pytest.raises(ToolError):
        directory.mark_dna_reminded("ten_missing", at=at)


# --- The shared run claim -------------------------------------------------------


def _record(
    run_id: str, *, tenant: str = TENANT, slug: str = SLUG, user: str = "usr_a"
) -> RunRecord:
    """Build a running run record.

    Args:
        run_id: The run's id.
        tenant: The tenant the run belongs to.
        slug: The campaign the run claims.
        user: The person claiming it.

    Returns:
        The record to claim.
    """
    return RunRecord(
        run_id=run_id,
        tenant_id=tenant,
        slug=slug,
        user_id=user,
        stage=None,
        status="running",
        started_at=time.time(),
    )


def test_a_colleague_is_refused_the_same_campaign(postgres_pool: Any) -> None:
    """The database constraint is what holds, not a check in Python."""
    store = PostgresRunStore(postgres_pool)
    held = new_run_id()
    store.claim(_record(held, user="usr_a"))

    with pytest.raises(RunConflictError) as refused:
        store.claim(_record(new_run_id(), user="usr_b"))

    assert refused.value.active_run_id == held
    assert refused.value.active_user_id == "usr_a"


def test_finishing_a_run_frees_its_campaign_for_a_colleague(postgres_pool: Any) -> None:
    store = PostgresRunStore(postgres_pool)
    first = new_run_id()
    store.claim(_record(first, user="usr_a"))

    store.finish(first, "completed")
    second = new_run_id()
    store.claim(_record(second, user="usr_b"))

    assert store.active_for_campaign(TENANT, SLUG) is not None
    assert store.active_for_campaign(TENANT, SLUG).run_id == second
    assert store.get(first, TENANT).status == "completed"


def test_a_run_halted_at_an_approval_gate_keeps_its_campaign_claim(postgres_pool: Any) -> None:
    """The claim is what stops a second run racing the one waiting on a person.

    The partial unique index has to cover ``awaiting_approval`` as well as
    ``running``, or a halted run's campaign quietly becomes free the moment it
    stops to ask (ADR-0015).
    """
    store = PostgresRunStore(postgres_pool)
    halted = new_run_id()
    store.claim(_record(halted, user="usr_a"))

    store.set_live_status(halted, AWAITING_APPROVAL)

    with pytest.raises(RunConflictError) as refused:
        store.claim(_record(new_run_id(), user="usr_b"))
    assert refused.value.active_run_id == halted
    assert store.active_for_campaign(TENANT, SLUG).run_id == halted


def test_resuming_a_halted_run_returns_it_to_running(postgres_pool: Any) -> None:
    store = PostgresRunStore(postgres_pool)
    run_id = new_run_id()
    store.claim(_record(run_id))
    store.set_live_status(run_id, AWAITING_APPROVAL)

    resumed = store.set_live_status(run_id, "running")

    assert resumed is not None
    assert store.get(run_id, TENANT).status == "running"


def test_a_run_waiting_on_a_person_is_not_swept_away_by_a_restart(postgres_pool: Any) -> None:
    """A deploy must not discard work the owner was about to approve."""
    store = PostgresRunStore(postgres_pool)
    halted = new_run_id()
    store.claim(_record(halted))
    store.set_live_status(halted, AWAITING_APPROVAL)

    reclaimed = store.reclaim_running("interrupted")

    assert reclaimed == []
    assert store.get(halted, TENANT).status == AWAITING_APPROVAL


def test_deliverable_versions_are_not_readable_across_tenants(postgres_pool: Any) -> None:
    """Row-level security backstops the version chain as it does the documents."""
    store = PostgresDeliverableStore(postgres_pool)
    store.append(TENANT, SLUG, "brand-strategy", "# ours", feedback=None)

    assert store.latest(OTHER_TENANT, SLUG, "brand-strategy") is None
    assert store.stages(OTHER_TENANT, SLUG) == []


def test_a_version_query_with_no_tenant_scope_returns_nothing(postgres_pool: Any) -> None:
    PostgresDeliverableStore(postgres_pool).append(TENANT, SLUG, "research", "# ours")

    with postgres_pool.connection() as connection:
        connection.execute("SELECT set_config(%s, %s, true)", (TENANT_SETTING, OTHER_TENANT))
        rows = connection.execute("SELECT stage_key FROM deliverable_versions").fetchall()

    assert rows == []


def test_the_database_assigns_the_version_number(postgres_pool: Any) -> None:
    """Numbering in the insert is what stops two writers both claiming version 3."""
    store = PostgresDeliverableStore(postgres_pool)
    store.append(TENANT, SLUG, "brand-strategy", "# v1")

    second = store.append(
        TENANT, SLUG, "brand-strategy", "# v2", feedback="sharper", feedback_source="human"
    )

    assert second.version == 2
    assert second.supersedes_version == 1
    assert store.version(TENANT, SLUG, "brand-strategy", 1).content == "# v1"


def test_a_deliverable_history_outlives_the_process_that_wrote_it(postgres_pool: Any) -> None:
    """A second store over the same pool stands in for the restarted service."""
    PostgresDeliverableStore(postgres_pool).append(
        TENANT, SLUG, "brand-strategy", "# v1", feedback=None
    )

    reopened = PostgresDeliverableStore(postgres_pool)

    assert reopened.latest(TENANT, SLUG, "brand-strategy").content == "# v1"


def test_two_tenants_may_hold_the_same_slug_at_once(postgres_pool: Any) -> None:
    store = PostgresRunStore(postgres_pool)
    mine = new_run_id()
    theirs = new_run_id()

    store.claim(_record(mine))
    store.claim(_record(theirs, tenant=OTHER_TENANT))

    assert [record.run_id for record in store.active(TENANT)] == [mine]
    assert [record.run_id for record in store.active(OTHER_TENANT)] == [theirs]


def test_a_run_belonging_to_another_tenant_is_unfindable(postgres_pool: Any) -> None:
    store = PostgresRunStore(postgres_pool)
    run_id = new_run_id()
    store.claim(_record(run_id))

    assert store.get(run_id, OTHER_TENANT) is None


def test_a_run_a_crash_left_running_is_reclaimed(postgres_pool: Any) -> None:
    """Survives a restart: the run is resolved, not left ``running`` forever."""
    store = PostgresRunStore(postgres_pool)
    abandoned = new_run_id()
    store.claim(_record(abandoned))

    reclaimed = store.reclaim_running("interrupted")

    assert [record.run_id for record in reclaimed] == [abandoned]
    assert store.get(abandoned, TENANT).status == "interrupted"
    assert store.active_for_campaign(TENANT, SLUG) is None


def test_reclaiming_leaves_finished_runs_alone(postgres_pool: Any) -> None:
    """A restart resolves live runs; it does not rewrite history."""
    store = PostgresRunStore(postgres_pool)
    finished = new_run_id()
    store.claim(_record(finished))
    store.finish(finished, "completed")

    assert store.reclaim_running("interrupted") == []
    assert store.get(finished, TENANT).status == "completed"


def test_a_late_callback_cannot_resurrect_a_cancelled_run(postgres_pool: Any) -> None:
    """A task finishing must not overwrite a cancellation that already landed."""
    store = PostgresRunStore(postgres_pool)
    run_id = new_run_id()
    store.claim(_record(run_id))
    store.finish(run_id, "cancelled")

    store.finish(run_id, "completed")

    assert store.get(run_id, TENANT).status == "cancelled"


# --- The durable checkpointer ---------------------------------------------------


async def test_a_run_checkpoint_outlives_the_process_that_wrote_it(
    settings: Settings,
    postgres_superuser_dsn: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The hard prerequisite for approval gates: state a later process can resume.

    Two savers, opened and closed independently, stand in for two processes: the
    second reads what the first wrote, which an in-process checkpointer cannot do.
    The saver is the **async** one because the runner drives the graph with
    ``astream`` (ADR-0009) — the synchronous saver has no async methods at all.
    """
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    install_scripted_graph(monkeypatch)
    thread = {"configurable": {"thread_id": thread_id(TENANT, SLUG, "research")}}

    async with AsyncPostgresSaver.from_conn_string(postgres_superuser_dsn) as writer:
        await writer.setup()
        adapters = {**prototype_adapters(settings.root), "checkpointer": writer}
        await arun_campaign(settings, TENANT, SLUG, stage="research", **adapters)

    async with AsyncPostgresSaver.from_conn_string(postgres_superuser_dsn) as reader:
        stored = await reader.aget_tuple(thread)

    assert stored is not None
    assert stored.checkpoint["channel_values"]["error"] is None


async def test_a_run_halted_at_a_gate_is_approvable_after_a_restart(
    settings: Settings,
    postgres_superuser_dsn: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The acceptance criterion the whole Postgres prerequisite exists for.

    Two savers opened and closed independently stand in for a deploy: the first
    process runs until the brand-strategy gate and goes away entirely; the second
    finds the run still waiting, approves it, and the pipeline continues into
    campaign strategy. Nothing of the first process survives but the database.
    """
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    write_all_agent_specs(settings)
    install_scripted_graph(monkeypatch)
    versions = InMemoryDeliverableStore()
    adapters = {**prototype_adapters(settings.root), "deliverable_store": versions}

    async with AsyncPostgresSaver.from_conn_string(postgres_superuser_dsn) as first:
        await first.setup()
        halted = await arun_campaign(settings, TENANT, SLUG, **{**adapters, "checkpointer": first})
    assert halted.awaiting_approval_stage == "brand-strategy"

    async with AsyncPostgresSaver.from_conn_string(postgres_superuser_dsn) as second:
        waiting = await awaiting_approval_stage(TENANT, SLUG, checkpointer=second)
        assert waiting == "brand-strategy"
        resumed = await arun_campaign(
            settings,
            TENANT,
            SLUG,
            **{**adapters, "checkpointer": second},
            resume=Command(resume={"stage_key": "brand-strategy", "approved": True}),
        )

    assert resumed.awaiting_approval_stage == "campaign-strategy"
    assert versions.latest(TENANT, SLUG, "campaign-strategy") is not None


async def test_a_run_holding_for_a_question_still_carries_it_after_a_restart(
    settings: Settings,
    postgres_superuser_dsn: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The questions the business must answer are read back from the database alone.

    Two savers stand in for a deploy, as in the approval test above: the first
    process halts on the specialist's question and goes away; the second finds
    the run still holding, with the same questions and reasons (ADR-0028).
    """
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    write_all_agent_specs(settings)
    install_scripted_graph(monkeypatch, handler=asking_handler("research"))
    adapters = prototype_adapters(settings.root)

    async with AsyncPostgresSaver.from_conn_string(postgres_superuser_dsn) as first:
        await first.setup()
        halted = await arun_campaign(settings, TENANT, SLUG, **{**adapters, "checkpointer": first})
    assert halted.awaiting_clarification_stage == "research"

    async with AsyncPostgresSaver.from_conn_string(postgres_superuser_dsn) as second:
        hold = await pending_hold(TENANT, SLUG, checkpointer=second)

    assert hold is not None
    assert hold.kind == "clarification"
    assert hold.stage == "research"
    assert [question.model_dump() for question in hold.questions] == ASK_QUESTIONS


async def test_a_run_holding_for_a_question_continues_after_a_restart_once_answered(
    settings: Settings,
    postgres_superuser_dsn: str,
    postgres_pool: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The acceptance criterion for answering: it works across a process boundary.

    Two savers stand in for a deploy, as the approval test does: the first
    process halts on the specialist's question and goes away; the second saves
    the answers through the Postgres answer store, renders the Brand DNA from
    what it reads back, resumes the run, and the stage re-runs from that DNA
    and continues to the next gate (ADR-0028).
    """
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    write_all_agent_specs(settings)
    install_scripted_graph(monkeypatch, handler=asking_until_answered_handler("research"))
    versions = InMemoryDeliverableStore()
    adapters = {**prototype_adapters(settings.root), "deliverable_store": versions}

    async with AsyncPostgresSaver.from_conn_string(postgres_superuser_dsn) as first:
        await first.setup()
        halted = await arun_campaign(settings, TENANT, SLUG, **{**adapters, "checkpointer": first})
    assert halted.awaiting_clarification_stage == "research"

    answers = PostgresAnswerStore(postgres_pool)
    answers.upsert(
        TENANT,
        version=SEED_QUESTIONNAIRE.version,
        answers=[
            DnaAnswer(question_id=question.id, answer=f"Answer to {question.field}")
            for question in SEED_QUESTIONNAIRE.required_questions
        ],
    )
    record = answers.add_clarifications(TENANT, clarifications=answered_clarifications("research"))
    adapters["document_store"].write(
        TENANT, "dna.md", render_brand_dna(SEED_QUESTIONNAIRE, record, business_name="Acme")
    )
    async with AsyncPostgresSaver.from_conn_string(postgres_superuser_dsn) as second:
        resumed = await arun_campaign(
            settings,
            TENANT,
            SLUG,
            **{**adapters, "checkpointer": second},
            resume=Command(resume={"answered": True}),
        )

    assert resumed.awaiting_clarification_stage is None
    assert resumed.awaiting_approval_stage == "brand-strategy"
    assert versions.latest(TENANT, SLUG, "research") is not None


async def test_clearing_a_campaigns_threads_removes_its_durable_state(
    settings: Settings,
    postgres_superuser_dsn: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Abandoning a cancelled run has to reach the database, not just a dict."""
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    install_scripted_graph(monkeypatch)
    thread = {"configurable": {"thread_id": thread_id(TENANT, SLUG, "research")}}

    async with AsyncPostgresSaver.from_conn_string(postgres_superuser_dsn) as saver:
        await saver.setup()
        adapters = {**prototype_adapters(settings.root), "checkpointer": saver}
        await arun_campaign(settings, TENANT, SLUG, stage="research", **adapters)
        assert await saver.aget_tuple(thread) is not None

        await clear_campaign_threads(saver, TENANT, SLUG)

        assert await saver.aget_tuple(thread) is None


# --- The questionnaire and Brand DNA answers ------------------------------------


def test_a_published_question_set_survives_the_process(postgres_pool: Any) -> None:
    store = PostgresQuestionnaireStore(postgres_pool)
    assert store.published().version == SEED_QUESTIONNAIRE.version  # falls back to the seed

    newer = SEED_QUESTIONNAIRE.model_copy(
        update={"version": SEED_QUESTIONNAIRE.version + 1, "published_at": "2026-09-02T09:00:00Z"}
    )
    store.publish(newer)

    reopened = PostgresQuestionnaireStore(postgres_pool)
    assert reopened.published().version == newer.version
    assert [q.id for q in reopened.published().questions] == [q.id for q in newer.questions]
    assert reopened.version(SEED_QUESTIONNAIRE.version).version == SEED_QUESTIONNAIRE.version


def test_a_query_with_no_tenant_scope_returns_no_answers_across_tenants(
    postgres_pool: Any,
) -> None:
    # The RLS policy is what makes this true, not the WHERE clause: the query
    # below deliberately has no tenant predicate at all.
    PostgresAnswerStore(postgres_pool).upsert(
        TENANT, version=1, answers=[DnaAnswer(question_id="q_price_point", answer="$90")]
    )
    with postgres_pool.connection() as connection:
        connection.execute("SELECT set_config(%s, %s, true)", (TENANT_SETTING, OTHER_TENANT))
        rows = connection.execute("SELECT question_id FROM dna_answers").fetchall()
    assert rows == []


def test_one_business_cannot_read_anothers_brand_dna_answers(postgres_pool: Any) -> None:
    store = PostgresAnswerStore(postgres_pool)
    store.upsert(TENANT, version=1, answers=[DnaAnswer(question_id="q_price_point", answer="$90")])
    assert store.read(TENANT).answer_for("q_price_point") == "$90"
    assert store.read(OTHER_TENANT).answers == []


def test_editing_one_answer_leaves_the_rest_and_advances_the_version(
    postgres_pool: Any,
) -> None:
    store = PostgresAnswerStore(postgres_pool)
    store.upsert(
        TENANT,
        version=1,
        answers=[
            DnaAnswer(question_id="q_business_name", answer="Acme"),
            DnaAnswer(question_id="q_price_point", answer="$90"),
        ],
    )
    store.upsert(TENANT, version=2, answers=[DnaAnswer(question_id="q_price_point", answer="$120")])

    record = store.read(TENANT)
    assert record.answer_for("q_business_name") == "Acme"
    assert record.answer_for("q_price_point") == "$120"
    assert record.questionnaire_version == 2
    assert record.updated_at is not None


def test_removing_an_answer_leaves_the_rest_and_is_scoped_to_one_tenant(
    postgres_pool: Any,
) -> None:
    store = PostgresAnswerStore(postgres_pool)
    store.upsert(
        TENANT,
        version=1,
        answers=[
            DnaAnswer(question_id="q_business_name", answer="Acme"),
            DnaAnswer(question_id="q_price_point", answer="$90"),
        ],
    )
    store.upsert(
        OTHER_TENANT, version=1, answers=[DnaAnswer(question_id="q_price_point", answer="$120")]
    )

    store.remove(TENANT, question_id="q_price_point")

    record = store.read(TENANT)
    assert record.answer_for("q_price_point") is None
    assert record.answer_for("q_business_name") == "Acme"
    assert store.read(OTHER_TENANT).answer_for("q_price_point") == "$120"


def test_removal_does_not_advance_the_last_saved_time(postgres_pool: Any) -> None:
    # The same contract the in-memory store keeps: a removal writes nothing, so
    # it must not read as a save.
    store = PostgresAnswerStore(postgres_pool)
    store.upsert(
        TENANT,
        version=1,
        answers=[
            DnaAnswer(question_id="q_business_name", answer="Acme"),
            DnaAnswer(question_id="q_price_point", answer="$90"),
        ],
    )
    saved_at = store.read(TENANT).updated_at

    assert store.remove(TENANT, question_id="q_price_point").updated_at == saved_at


def test_a_blank_answer_row_written_before_the_rule_is_still_readable(
    postgres_pool: Any,
) -> None:
    # The shipped code could store a blank answer, so rows like this exist. The
    # rule refusing new ones must not make an existing one unreadable: that
    # would take the whole Brand DNA — and the gate with it — down for that
    # business, which is worse than the blank it was meant to prevent.
    from marketing_os.adapters.postgres.schema import TENANT_SETTING

    with postgres_pool.connection() as connection:
        connection.execute("SELECT set_config(%s, %s, true)", (TENANT_SETTING, TENANT))
        connection.execute(
            "INSERT INTO dna_answers "
            "(tenant_id, question_id, answer, questionnaire_version) VALUES (%s, %s, %s, %s)",
            (TENANT, "q_price_point", "   ", 1),
        )

    record = PostgresAnswerStore(postgres_pool).read(TENANT)

    assert record.answer_for("q_price_point") == "   "


def test_removing_an_unanswered_question_changes_nothing(postgres_pool: Any) -> None:
    store = PostgresAnswerStore(postgres_pool)
    store.upsert(TENANT, version=1, answers=[DnaAnswer(question_id="q_price_point", answer="$90")])

    store.remove(TENANT, question_id="q_business_name")

    assert store.read(TENANT).answer_for("q_price_point") == "$90"


def test_publishing_a_question_set_changes_what_the_gate_requires(
    postgres_pool: Any, tmp_path: Any
) -> None:
    from marketing_os.entrypoints.cli import load_questionnaire_file
    from marketing_os.schemas import Question, Questionnaire

    tightened = Questionnaire(
        version=SEED_QUESTIONNAIRE.version + 1,
        published_at="2026-09-02T09:00:00Z",
        questions=[
            *SEED_QUESTIONNAIRE.questions,
            Question(
                id="q_seasonality",
                field="Seasonality",
                section="Reach & constraints",
                text="When is your busiest season?",
                why_we_ask="Timing a campaign against demand changes what it says.",
                help_text="Name the months.",
                required=True,
            ),
        ],
    )
    path = tmp_path / "questions.json"
    path.write_text(tightened.model_dump_json(), encoding="utf-8")

    store = PostgresQuestionnaireStore(postgres_pool)
    store.publish(load_questionnaire_file(path))

    published = PostgresQuestionnaireStore(postgres_pool).published()
    assert published.version == tightened.version
    assert "Seasonality" in [question.field for question in published.required_questions]


def test_clarifications_are_read_back_beside_the_answers(postgres_pool: Any) -> None:
    """One read renders the whole Brand DNA: questionnaire answers and Clarifications."""
    store = PostgresAnswerStore(postgres_pool)
    store.upsert(TENANT, version=1, answers=[DnaAnswer(question_id="q_price_point", answer="$50")])
    email_list = answered_clarifications("research")[0]

    record = store.add_clarifications(TENANT, clarifications=[email_list])

    assert record.answer_for("q_price_point") == "$50"
    assert record.clarifications == [email_list]
    assert PostgresAnswerStore(postgres_pool).read(TENANT).clarifications == [email_list]
    assert CLARIFICATIONS_HEADING in render_brand_dna(
        SEED_QUESTIONNAIRE, record, business_name="Acme"
    )


def test_clarifications_answered_together_keep_the_order_they_were_asked_in(
    postgres_pool: Any,
) -> None:
    """One save stamps every answer with the same time, so the time cannot order them."""
    store = PostgresAnswerStore(postgres_pool)
    asked = answered_clarifications("research")
    reversed_ids = [
        item.model_copy(update={"id": f"clr_{9 - index}"}) for index, item in enumerate(asked)
    ]

    store.add_clarifications(TENANT, clarifications=reversed_ids)

    assert [item.question for item in store.read(TENANT).clarifications] == [
        item.question for item in asked
    ]


def test_one_business_cannot_read_anothers_clarifications(postgres_pool: Any) -> None:
    store = PostgresAnswerStore(postgres_pool)
    store.add_clarifications(TENANT, clarifications=answered_clarifications("research"))

    assert store.read(OTHER_TENANT).clarifications == []
    with postgres_pool.connection() as connection:
        connection.execute("SELECT set_config(%s, %s, true)", (TENANT_SETTING, OTHER_TENANT))
        rows = connection.execute("SELECT clarification_id FROM dna_clarifications").fetchall()
    assert rows == []


def test_a_clarification_answer_can_be_edited_in_place(postgres_pool: Any) -> None:
    """The edit changes one answer; the others, and the order, stay as they were."""
    store = PostgresAnswerStore(postgres_pool)
    first, second = answered_clarifications("research")
    store.add_clarifications(TENANT, clarifications=[first, second])

    record = store.update_clarification(
        TENANT, clarification_id=first.id, answer="No list yet; we collect emails at the desk."
    )

    edited, kept = record.clarifications
    assert edited.answer == "No list yet; we collect emails at the desk."
    assert edited.answered_at != first.answered_at
    assert edited.model_dump(exclude={"answer", "answered_at"}) == first.model_dump(
        exclude={"answer", "answered_at"}
    )
    assert kept == second
    assert store.read(TENANT).clarifications == [edited, kept]


def test_one_business_cannot_edit_anothers_clarification(postgres_pool: Any) -> None:
    """A foreign id is indistinguishable from a missing one, and the owner's answer stands."""
    store = PostgresAnswerStore(postgres_pool)
    email_list = answered_clarifications("research")[0]
    store.add_clarifications(TENANT, clarifications=[email_list])

    with pytest.raises(DocumentNotFoundError):
        store.update_clarification(OTHER_TENANT, clarification_id=email_list.id, answer="x")
    with pytest.raises(DocumentNotFoundError):
        store.update_clarification(TENANT, clarification_id="clr_missing", answer="x")

    assert store.read(TENANT).clarifications == [email_list]


def test_a_run_holding_for_a_clarification_keeps_its_campaign_claim(postgres_pool: Any) -> None:
    """A run asking the business a question is waiting on a person too (ADR-0028).

    The partial unique index has to cover ``awaiting_clarification`` as it does
    ``awaiting_approval``, or the campaign quietly becomes free the moment its
    specialist stops to ask.
    """
    store = PostgresRunStore(postgres_pool)
    asking = new_run_id()
    store.claim(_record(asking, user="usr_a"))

    store.set_live_status(asking, AWAITING_CLARIFICATION)

    with pytest.raises(RunConflictError) as refused:
        store.claim(_record(new_run_id(), user="usr_b"))
    assert refused.value.active_run_id == asking
    assert store.active_for_campaign(TENANT, SLUG).run_id == asking

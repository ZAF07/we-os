"""Postgres questionnaire and answer stores — the production adapters.

Implements :class:`~marketing_os.ports.QuestionnaireStore` and
:class:`~marketing_os.ports.AnswerStore` (ADR-0018), behaving identically to the
in-memory adapters in :mod:`marketing_os.adapters.questionnaire` so the same
assertions hold against both.

The question set is platform-wide, so its queries carry no tenant. The answers
are tenant-partitioned, so every one of their transactions sets
``marketing_os.tenant_id`` first — exactly as the document store does — and the
``dna_answers_tenant_isolation`` policy scopes the query even if the SQL did not.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from marketing_os.adapters.documents import validate_tenant_id
from marketing_os.adapters.postgres.schema import TENANT_SETTING
from marketing_os.adapters.questionnaire import UNANSWERED_VERSION, validate_publication
from marketing_os.questionnaire import SEED_QUESTIONNAIRE
from marketing_os.schemas import BrandDnaRecord, DnaAnswer, Question, Questionnaire


def _to_questionnaire(version: int, published_at: Any, questions: Any) -> Questionnaire:
    """Build a questionnaire from one ``questionnaires`` row.

    Args:
        version: The published version number.
        published_at: The publication timestamp as psycopg returns it.
        questions: The questions as stored JSON.

    Returns:
        The questionnaire the row records.
    """
    return Questionnaire(
        version=version,
        published_at=published_at.isoformat()
        if hasattr(published_at, "isoformat")
        else str(published_at),
        questions=[Question.model_validate(item) for item in questions],
    )


class PostgresQuestionnaireStore:
    """Serves the published question set from the ``questionnaires`` table."""

    def __init__(self, pool: Any, seed: Questionnaire = SEED_QUESTIONNAIRE) -> None:
        """Initialise the store.

        Args:
            pool: A ``psycopg_pool.ConnectionPool``.
            seed: The question set served until an admin publishes one, so a
                freshly provisioned database still has a usable onboarding.
        """
        self._pool = pool
        self._seed = seed

    def published(self) -> Questionnaire:
        """Return the currently published question set.

        Returns:
            The highest published version, or the code-shipped seed when the
            table is empty.
        """
        with self._pool.connection() as connection:
            row = connection.execute(
                "SELECT version, published_at, questions FROM questionnaires "
                "ORDER BY version DESC LIMIT 1"
            ).fetchone()
        if row is None:
            return self._seed
        return _to_questionnaire(row[0], row[1], row[2])

    def version(self, version: int) -> Questionnaire | None:
        """Return one published version by number.

        Args:
            version: The published version number.

        Returns:
            That version, or ``None`` when it was never published. The seed is
            reported for its own version number while the table is empty, so the
            fallback in :meth:`published` stays consistent.
        """
        with self._pool.connection() as connection:
            row = connection.execute(
                "SELECT version, published_at, questions FROM questionnaires WHERE version = %s",
                (version,),
            ).fetchone()
        if row is None:
            return self._seed if version == self._seed.version else None
        return _to_questionnaire(row[0], row[1], row[2])

    def publish(self, questionnaire: Questionnaire) -> Questionnaire:
        """Publish a new version of the question set.

        Args:
            questionnaire: The version to publish.

        Returns:
            The published version.

        Raises:
            ValidationError: If the version does not advance past the current one.
        """
        from psycopg.types.json import Jsonb

        validate_publication(questionnaire, self.published().version)
        payload = [question.model_dump() for question in questionnaire.questions]
        with self._pool.connection() as connection:
            connection.execute(
                "INSERT INTO questionnaires (version, published_at, questions) VALUES (%s, %s, %s)",
                (questionnaire.version, questionnaire.published_at, Jsonb(payload)),
            )
        return questionnaire


class PostgresAnswerStore:
    """Serves each business's Brand DNA answers from the ``dna_answers`` table."""

    def __init__(self, pool: Any) -> None:
        """Initialise the store.

        Args:
            pool: A ``psycopg_pool.ConnectionPool`` whose connections belong to
                the application role (not a superuser, which bypasses RLS).
        """
        self._pool = pool

    @contextmanager
    def _scoped_to(self, tenant: str) -> Iterator[tuple[Any, str]]:
        """Open a transaction that may only touch one tenant's answers.

        Args:
            tenant: The tenant every statement in the transaction may touch.

        Yields:
            The open connection and the validated tenant id.

        Raises:
            ToolError: If the tenant id is malformed.
        """
        scoped_tenant = validate_tenant_id(tenant)
        with self._pool.connection() as connection:
            connection.execute("SELECT set_config(%s, %s, true)", (TENANT_SETTING, scoped_tenant))
            yield connection, scoped_tenant

    def read(self, tenant: str) -> BrandDnaRecord:
        """Return a business's answers.

        Args:
            tenant: The tenant whose answers to read.

        Returns:
            The record, empty at version 0 when nothing has been answered. The
            recorded version is the highest any answer was given against, so a
            business part-way through a newer question set is treated as being
            on that newer set.
        """
        with self._scoped_to(tenant) as (connection, scoped):
            rows = connection.execute(
                "SELECT question_id, answer, questionnaire_version, updated_at "
                "FROM dna_answers WHERE tenant_id = %s ORDER BY question_id",
                (scoped,),
            ).fetchall()
        if not rows:
            return BrandDnaRecord(questionnaire_version=UNANSWERED_VERSION)
        updated_at = max(row[3] for row in rows)
        return BrandDnaRecord(
            questionnaire_version=max(row[2] for row in rows),
            updated_at=updated_at.isoformat().replace("+00:00", "Z"),
            answers=[DnaAnswer(question_id=row[0], answer=row[1]) for row in rows],
        )

    def upsert(self, tenant: str, *, version: int, answers: list[DnaAnswer]) -> BrandDnaRecord:
        """Save answers, replacing any previous answer to the same question.

        Args:
            tenant: The tenant the answers belong to.
            version: The question-set version the answers were given against.
            answers: The answers to save.

        Returns:
            The business's full record after the save.
        """
        with self._scoped_to(tenant) as (connection, scoped):
            for answer in answers:
                connection.execute(
                    "INSERT INTO dna_answers "
                    "(tenant_id, question_id, answer, questionnaire_version) "
                    "VALUES (%s, %s, %s, %s) "
                    "ON CONFLICT (tenant_id, question_id) DO UPDATE SET "
                    "answer = EXCLUDED.answer, "
                    "questionnaire_version = EXCLUDED.questionnaire_version, "
                    "updated_at = now()",
                    (scoped, answer.question_id, answer.answer, version),
                )
        return self.read(tenant)

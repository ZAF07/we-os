"""In-memory questionnaire and answer stores — the fast suite's and local default.

Implements :class:`~marketing_os.ports.QuestionnaireStore` and
:class:`~marketing_os.ports.AnswerStore` (ADR-0018). The Postgres adapters in
:mod:`marketing_os.adapters.postgres.questionnaire` behave identically and pass
the same assertions; these hold everything in dicts so no test touches a database.

The questionnaire store falls back to the code-shipped seed until an admin
publishes a version, so a deployment with an empty table still has a usable
onboarding rather than an empty wizard.
"""

from __future__ import annotations

from datetime import UTC, datetime

from marketing_os.errors import ValidationError
from marketing_os.questionnaire import SEED_QUESTIONNAIRE
from marketing_os.schemas import BrandDnaRecord, DnaAnswer, Questionnaire

UNANSWERED_VERSION = 0


def now_iso() -> str:
    """Return the current UTC time as an ISO-8601 timestamp.

    Returns:
        The timestamp, second-resolution, with a trailing ``Z``.
    """
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def validate_publication(questionnaire: Questionnaire, current_version: int) -> Questionnaire:
    """Check a version advances past the currently published one.

    Shared by both adapters so "you cannot republish an older set" is one rule
    rather than two implementations of it: an older version would loosen the DNA
    Gate for every business at once, silently.

    Args:
        questionnaire: The version being published.
        current_version: The currently published version.

    Returns:
        The questionnaire, unchanged.

    Raises:
        ValidationError: If the version does not advance.
    """
    if questionnaire.version <= current_version:
        raise ValidationError(
            f"Questionnaire version {questionnaire.version} does not advance past the "
            f"published version {current_version}. Publish a higher version."
        )
    return questionnaire


class InMemoryQuestionnaireStore:
    """Holds published question-set versions in a dict, newest wins."""

    def __init__(self, seed: Questionnaire = SEED_QUESTIONNAIRE) -> None:
        """Initialise the store with the version served before anything is published.

        Args:
            seed: The question set to serve until an admin publishes a newer one.
        """
        self._seed = seed
        self._versions: dict[int, Questionnaire] = {}

    def published(self) -> Questionnaire:
        """Return the currently published question set.

        Returns:
            The highest published version, or the seed when nothing is published.
        """
        if not self._versions:
            return self._seed
        return self._versions[max(self._versions)]

    def version(self, version: int) -> Questionnaire | None:
        """Return one published version by number.

        Args:
            version: The published version number.

        Returns:
            That version, or ``None`` when it was never published.
        """
        if version == self._seed.version and version not in self._versions:
            return self._seed
        return self._versions.get(version)

    def publish(self, questionnaire: Questionnaire) -> Questionnaire:
        """Publish a new version of the question set.

        Args:
            questionnaire: The version to publish.

        Returns:
            The published version.

        Raises:
            ValidationError: If the version does not advance past the current one.
        """
        validate_publication(questionnaire, self.published().version)
        self._versions[questionnaire.version] = questionnaire
        return questionnaire


class InMemoryAnswerStore:
    """Holds each tenant's Brand DNA answers in a dict, keyed by tenant.

    Keying on the tenant gives the same guarantee the in-memory document store
    gives: a read that does not name the owning tenant simply misses.
    """

    def __init__(self) -> None:
        """Initialise the empty store."""
        self._records: dict[str, BrandDnaRecord] = {}

    def read(self, tenant: str) -> BrandDnaRecord:
        """Return a business's answers.

        Args:
            tenant: The tenant whose answers to read.

        Returns:
            The record, empty at version 0 when nothing has been answered.
        """
        existing = self._records.get(tenant)
        if existing is None:
            return BrandDnaRecord(questionnaire_version=UNANSWERED_VERSION)
        return existing.model_copy(deep=True)

    def upsert(self, tenant: str, *, version: int, answers: list[DnaAnswer]) -> BrandDnaRecord:
        """Save answers, replacing any previous answer to the same question.

        Args:
            tenant: The tenant the answers belong to.
            version: The question-set version the answers were given against.
            answers: The answers to save.

        Returns:
            The business's full record after the save.
        """
        merged = {answer.question_id: answer.answer for answer in self.read(tenant).answers}
        merged.update({answer.question_id: answer.answer for answer in answers})
        record = BrandDnaRecord(
            questionnaire_version=version,
            updated_at=now_iso(),
            answers=[
                DnaAnswer(question_id=question_id, answer=text)
                for question_id, text in merged.items()
            ],
        )
        self._records[tenant] = record
        return record.model_copy(deep=True)

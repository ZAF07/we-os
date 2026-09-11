"""A Brand DNA review is due: derived from one timestamp, never stored (ADR-0028).

Facts about a business drift, so the platform asks the owner to look at their
Brand DNA again on an interval. What is pinned here is what an owner or an
operator can observe: the review read says whether one is due, every write to
the DNA counts as a review, marking it reviewed clears it, and the interval is
a setting the next read honours. The clock is faked so "a week later" is a
test, not a wait.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from conftest import (
    SLUG,
    answered_clarifications,
    asking_until_answered_handler,
    clear_prototype_adapters,
    filled_dna_answers,
    identity_for,
    install_prototype_adapters,
    install_scripted_graph,
    write_all_agent_specs,
)
from marketing_os.adapters.tenants import InMemoryTenantDirectory, PassthroughTenantDirectory
from marketing_os.config import Settings, parse_duration
from marketing_os.errors import ConfigError, ToolError
from marketing_os.questionnaire import SEED_QUESTIONNAIRE, render_brand_dna
from marketing_os.questionnaire.review import dna_review

CLERK_ORG = "org_3IlRVjdAue93iyWDYAQYGLHcjBx"
T0 = datetime(2026, 9, 11, 9, 0, tzinfo=UTC)
WEEK = timedelta(days=7)


# --- The interval setting -------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("7d", timedelta(days=7)),
        ("1m", timedelta(minutes=1)),
        ("20s", timedelta(seconds=20)),
        ("12h", timedelta(hours=12)),
        ("90", timedelta(seconds=90)),
        (" 2D ", timedelta(days=2)),
    ],
)
def test_the_interval_is_written_as_a_duration(raw: str, expected: timedelta) -> None:
    assert parse_duration(raw) == expected


@pytest.mark.parametrize("raw", ["", "soon", "7w", "-1d", "0s", "1.5h"])
def test_a_duration_that_is_not_one_is_refused(raw: str) -> None:
    with pytest.raises(ConfigError):
        parse_duration(raw)


def test_the_review_interval_defaults_to_a_week(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MARKETING_OS_DNA_REVIEW_INTERVAL", raising=False)

    assert Settings().dna_review_interval == WEEK


def test_the_review_interval_is_read_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MARKETING_OS_DNA_REVIEW_INTERVAL", "1m")

    assert Settings().dna_review_interval == timedelta(minutes=1)


# --- Due-ness, as a pure function -----------------------------------------------


def test_a_review_is_due_once_more_than_the_interval_has_passed() -> None:
    review = dna_review(
        reviewed_at=T0,
        dna_updated_at=None,
        complete=True,
        now=T0 + WEEK + timedelta(seconds=1),
        interval=WEEK,
    )

    assert review.due is True
    assert review.reviewed_at == T0


def test_a_review_is_not_due_at_exactly_the_interval() -> None:
    review = dna_review(
        reviewed_at=T0, dna_updated_at=None, complete=True, now=T0 + WEEK, interval=WEEK
    )

    assert review.due is False


def test_a_tenant_that_never_reviewed_counts_from_when_its_answers_were_saved() -> None:
    saved = T0 - timedelta(days=30)

    review = dna_review(
        reviewed_at=None, dna_updated_at=saved, complete=True, now=T0, interval=WEEK
    )

    assert review.due is True
    assert review.reviewed_at == saved


def test_a_recorded_review_wins_over_when_the_answers_were_saved() -> None:
    review = dna_review(
        reviewed_at=T0,
        dna_updated_at=T0 - timedelta(days=30),
        complete=True,
        now=T0 + timedelta(days=1),
        interval=WEEK,
    )

    assert review.due is False
    assert review.reviewed_at == T0


def test_a_business_with_no_dna_has_nothing_to_review() -> None:
    review = dna_review(
        reviewed_at=None, dna_updated_at=None, complete=False, now=T0, interval=WEEK
    )

    assert review.due is False
    assert review.reviewed_at is None


def test_an_incomplete_dna_is_owed_answers_not_a_review() -> None:
    """The Setup item already stands for an unfinished DNA; a Review beside it is noise."""
    review = dna_review(
        reviewed_at=T0 - timedelta(days=30),
        dna_updated_at=None,
        complete=False,
        now=T0,
        interval=WEEK,
    )

    assert review.due is False


# --- The directories ------------------------------------------------------------


def test_a_new_tenant_has_never_been_reviewed() -> None:
    directory = InMemoryTenantDirectory()

    assert (
        directory.resolve(external_auth_id=CLERK_ORG, name="Coast Coffee").dna_reviewed_at is None
    )


def test_marking_a_review_records_when_and_every_path_reads_it_back() -> None:
    directory = InMemoryTenantDirectory()
    tenant = directory.resolve(external_auth_id=CLERK_ORG, name="Coast Coffee")

    marked = directory.mark_dna_reviewed(tenant.tenant_id, at=T0)

    assert marked.dna_reviewed_at == T0
    assert marked.tenant_id == tenant.tenant_id
    found = directory.get(tenant.tenant_id)
    assert found is not None and found.dna_reviewed_at == T0
    assert directory.resolve(external_auth_id=CLERK_ORG, name="Coast Coffee").dna_reviewed_at == T0


def test_marking_again_moves_the_review_forward() -> None:
    directory = InMemoryTenantDirectory()
    tenant = directory.resolve(external_auth_id=CLERK_ORG, name="Coast Coffee")
    directory.mark_dna_reviewed(tenant.tenant_id, at=T0)

    later = directory.mark_dna_reviewed(tenant.tenant_id, at=T0 + WEEK)

    assert later.dna_reviewed_at == T0 + WEEK


def test_marking_keeps_the_tier_and_the_name() -> None:
    directory = InMemoryTenantDirectory()
    tenant = directory.resolve(external_auth_id=CLERK_ORG, name="Coast Coffee")
    directory.set_tier(tenant.tenant_id, "operator")

    marked = directory.mark_dna_reviewed(tenant.tenant_id, at=T0)

    assert marked.tier == "operator"
    assert marked.name == "Coast Coffee"


def test_a_review_cannot_be_marked_for_a_tenant_that_was_never_registered() -> None:
    with pytest.raises(ToolError):
        InMemoryTenantDirectory().mark_dna_reviewed("ten_never_registered", at=T0)


def test_the_passthrough_directory_holds_no_review() -> None:
    """The filesystem layer has no table to keep a timestamp in, so it never reports one."""
    directory = PassthroughTenantDirectory()
    tenant = directory.resolve(external_auth_id=CLERK_ORG, name="Coast Coffee")

    accepted = directory.mark_dna_reviewed(tenant.tenant_id, at=T0)

    assert accepted.dna_reviewed_at is None
    found = directory.get(tenant.tenant_id)
    assert found is not None and found.dna_reviewed_at is None


# --- Through the API ------------------------------------------------------------


class FakeClock:
    """A clock the tests move by hand.

    Attributes:
        now: The instant the API reads as the current time.
    """

    def __init__(self, now: datetime) -> None:
        """Start the clock.

        Args:
            now: The first instant it reports.
        """
        self.now = now

    def advance(self, by: timedelta) -> None:
        """Move the clock forward.

        Args:
            by: How far.
        """
        self.now += by

    def __call__(self) -> datetime:
        """Return the current instant.

        Returns:
            The instant the clock is set to.
        """
        return self.now


class ReviewApi:
    """The entered client, the fake clock behind it, and the tenant it acts as.

    Attributes:
        client: The entered FastAPI test client.
        clock: The clock the API reads.
        tenant_id: The platform id of the business the client acts for.
        directory: The minting directory the tenant is registered in.
    """

    def __init__(
        self,
        client: TestClient,
        clock: FakeClock,
        tenant_id: str,
        directory: InMemoryTenantDirectory,
    ) -> None:
        """Hold the pieces a review test needs.

        Args:
            client: The entered FastAPI test client.
            clock: The clock the API reads.
            tenant_id: The platform id of the business the client acts for.
            directory: The minting directory the tenant is registered in.
        """
        self.client = client
        self.clock = clock
        self.tenant_id = tenant_id
        self.directory = directory

    def review(self) -> dict:
        """Read whether a review is due.

        Returns:
            The review payload.
        """
        response = self.client.get("/brand-dna/review")
        assert response.status_code == 200, response.text
        return response.json()

    def answer_everything(self) -> None:
        """Answer every Required question, completing the Brand DNA."""
        response = self.client.post(
            "/brand-dna/answers",
            json={
                "answers": [
                    {"question_id": question.id, "answer": f"Answer to {question.field}"}
                    for question in SEED_QUESTIONNAIRE.required_questions
                ]
            },
        )
        assert response.status_code == 200, response.text


@pytest.fixture
def api(repo: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[ReviewApi]:
    """Yield a hermetic API acting as a freshly registered business, on a fake clock.

    The prototype backend's passthrough directory keeps no tenant row, so the
    tenant is registered in a minting directory instead — the one that behaves
    as the Postgres directory does — and the identity acts as the id it minted.

    Args:
        repo: The hermetic repository root fixture.
        monkeypatch: The pytest monkeypatch fixture.

    Yields:
        The entered client with its clock and tenant.
    """
    monkeypatch.setenv("MARKETING_OS_ROOT", str(repo))
    monkeypatch.setenv("MARKETING_OS_DNA_REVIEW_INTERVAL", "7d")
    import marketing_os.entrypoints.api.app as api_module

    api_module.get_settings.cache_clear()
    install_prototype_adapters(repo)
    directory = InMemoryTenantDirectory()
    tenant = directory.resolve(external_auth_id=CLERK_ORG, name="Acme Climbing Gym")
    clock = FakeClock(T0)
    monkeypatch.setattr(api_module, "get_tenant_directory", lambda: directory)
    monkeypatch.setattr(api_module, "get_clock", lambda: clock)
    api_module.app.dependency_overrides[api_module.get_identity] = lambda: identity_for(
        tenant.tenant_id
    )
    with TestClient(api_module.app) as client:
        yield ReviewApi(client, clock, tenant.tenant_id, directory)
    api_module.app.dependency_overrides.clear()
    api_module.get_settings.cache_clear()
    clear_prototype_adapters()


def test_a_business_that_has_answered_nothing_has_no_review_due(api: ReviewApi) -> None:
    assert api.review() == {"due": False, "reviewed_at": None}


def test_a_dna_just_completed_is_not_due_until_the_interval_has_passed(api: ReviewApi) -> None:
    api.answer_everything()

    assert api.review()["due"] is False
    api.clock.advance(WEEK)
    assert api.review()["due"] is False
    api.clock.advance(timedelta(seconds=1))
    assert api.review()["due"] is True


def test_the_review_reports_when_the_dna_was_last_reviewed(api: ReviewApi) -> None:
    api.answer_everything()

    assert api.review()["reviewed_at"] == "2026-09-11T09:00:00Z"


def test_marking_reviewed_clears_it_for_another_interval(api: ReviewApi) -> None:
    api.answer_everything()
    api.clock.advance(WEEK + timedelta(hours=1))
    assert api.review()["due"] is True

    response = api.client.post("/brand-dna/review")

    assert response.status_code == 200, response.text
    assert response.json() == {"due": False, "reviewed_at": "2026-09-18T10:00:00Z"}
    assert api.review()["due"] is False
    api.clock.advance(WEEK + timedelta(seconds=1))
    assert api.review()["due"] is True


def test_saving_a_questionnaire_answer_counts_as_a_review(api: ReviewApi) -> None:
    api.answer_everything()
    api.clock.advance(WEEK + timedelta(hours=1))
    assert api.review()["due"] is True
    question = SEED_QUESTIONNAIRE.required_questions[0]

    api.client.post(
        "/brand-dna/answers",
        json={"answers": [{"question_id": question.id, "answer": "Looked at, still true."}]},
    )

    assert api.review()["due"] is False


def test_deleting_an_answer_counts_as_a_review_too(api: ReviewApi) -> None:
    """Withdrawing an answer is editing the DNA, and it leaves the DNA owed answers, not a look."""
    api.answer_everything()
    api.clock.advance(WEEK + timedelta(hours=1))
    question = SEED_QUESTIONNAIRE.required_questions[0]

    api.client.delete(f"/brand-dna/answers/{question.id}")

    assert api.review()["due"] is False
    found = api.directory.get(api.tenant_id)
    assert found is not None and found.dna_reviewed_at == api.clock.now


def test_editing_a_clarification_counts_as_a_review(api: ReviewApi) -> None:
    api.answer_everything()
    from marketing_os.entrypoints.api.app import get_answer_store

    record = get_answer_store().add_clarifications(
        api.tenant_id, clarifications=answered_clarifications("brand-strategy")
    )
    api.clock.advance(WEEK + timedelta(hours=1))
    assert api.review()["due"] is True

    response = api.client.put(
        f"/brand-dna/clarifications/{record.clarifications[0].id}",
        json={"answer": "Still about 1,200."},
    )

    assert response.status_code == 200, response.text
    assert api.review()["due"] is False


def test_the_interval_is_read_from_settings_on_every_read(
    api: ReviewApi, monkeypatch: pytest.MonkeyPatch
) -> None:
    api.answer_everything()
    api.clock.advance(timedelta(days=2))
    assert api.review()["due"] is False

    monkeypatch.setenv("MARKETING_OS_DNA_REVIEW_INTERVAL", "1d")
    import marketing_os.entrypoints.api.app as api_module

    api_module.get_settings.cache_clear()

    assert api.review()["due"] is True


def test_an_unauthenticated_caller_gets_no_review(api: ReviewApi) -> None:
    import marketing_os.entrypoints.api.app as api_module

    api_module.app.dependency_overrides.pop(api_module.get_identity)

    assert api.client.get("/brand-dna/review").status_code == 401
    assert api.client.post("/brand-dna/review").status_code == 401


def test_one_business_review_is_not_anothers(api: ReviewApi) -> None:
    api.answer_everything()
    api.clock.advance(WEEK + timedelta(hours=1))
    assert api.review()["due"] is True
    import marketing_os.entrypoints.api.app as api_module

    rival = api.directory.resolve(external_auth_id="org_rival", name="Rival")
    api_module.app.dependency_overrides[api_module.get_identity] = lambda: identity_for(
        rival.tenant_id
    )
    api.client.post("/brand-dna/review")
    api_module.app.dependency_overrides[api_module.get_identity] = lambda: identity_for(
        api.tenant_id
    )

    assert api.review()["due"] is True


def _wait_for_status(client: TestClient, run_id: str, target: str) -> None:
    """Poll a run's status until it reaches ``target`` or time out.

    Args:
        client: The entered test client.
        run_id: The run id to poll.
        target: The status to wait for.

    Raises:
        AssertionError: If the run never reaches ``target``.
    """
    for _ in range(300):
        response = client.get(f"/runs/{run_id}")
        if response.status_code == 200 and response.json()["status"] == target:
            return
        time.sleep(0.02)
    raise AssertionError(f"run {run_id} never reached status {target!r}")


def test_answering_a_runs_questions_counts_as_a_review(
    api: ReviewApi, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The owner just wrote a fact into their DNA; asking them to review it now would be absurd."""
    from conftest import _GOAL_FILLED, ASK_QUESTIONS, _write

    api.answer_everything()
    tenant_dir = repo / "tenants" / api.tenant_id
    _write(
        tenant_dir / "dna.md",
        render_brand_dna(SEED_QUESTIONNAIRE, filled_dna_answers(), business_name="Acme"),
    )
    _write(tenant_dir / "campaigns" / SLUG / "goal.md", _GOAL_FILLED)
    write_all_agent_specs(Settings(root=repo))
    install_scripted_graph(monkeypatch, handler=asking_until_answered_handler("brand-strategy"))
    run_id = api.client.post(f"/campaigns/{SLUG}/run", json={}).json()["run_id"]
    _wait_for_status(api.client, run_id, "awaiting_clarification")
    api.clock.advance(WEEK + timedelta(hours=1))
    assert api.review()["due"] is True

    response = api.client.post(
        f"/runs/{run_id}/clarifications",
        json={
            "answers": [
                {"question": question["question"], "answer": "About 1,200."}
                for question in ASK_QUESTIONS
            ]
        },
    )

    assert response.status_code == 202, response.text
    assert api.review()["due"] is False
    _wait_for_status(api.client, run_id, "awaiting_approval")

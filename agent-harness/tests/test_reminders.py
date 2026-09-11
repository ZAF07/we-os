"""The reminder email: when a review is due, the owner hears about it once (ADR-0028).

What is pinned here is what an owner or an operator can observe. The mailer is
a setting, and the real one is built only when it is selected, so no test or
local run can email a real address. One tick of the reminder task sends one
email per due tenant and none to anyone else, and a second tick within the
period sends nothing. The loop starts with the API, survives a failing tick,
and stops when the API does. The clock is faked so "a week later" is a test,
not a wait.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from conftest import clear_prototype_adapters, install_prototype_adapters
from marketing_os.adapters.mail import NoopMailer, ResendMailer, build_mailer
from marketing_os.adapters.questionnaire import InMemoryAnswerStore, InMemoryQuestionnaireStore
from marketing_os.adapters.tenants import InMemoryTenantDirectory
from marketing_os.config import MailerName, Settings
from marketing_os.errors import ConfigError, ToolError
from marketing_os.ports import Mailer
from marketing_os.questionnaire import SEED_QUESTIONNAIRE, DnaReview, reminder_due
from marketing_os.reminders import remind_on_interval, send_due_reminders
from marketing_os.schemas import DnaAnswer, EmailMessage

T0 = datetime(2026, 9, 11, 9, 0, tzinfo=UTC)
WEEK = timedelta(days=7)
APP_URL = "https://app.we-os.example"

MESSAGE = EmailMessage(
    to="sam@coastcoffee.example",
    subject="Your Brand DNA is due a review",
    text="Take a look at https://app.we-os.example/brand",
)

# --- The settings ---------------------------------------------------------------


def test_the_mailer_is_the_no_op_unless_one_is_chosen(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MARKETING_OS_MAILER", raising=False)

    assert Settings().mailer == MailerName.NOOP


def test_the_mailer_is_read_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MARKETING_OS_MAILER", " Resend ")

    assert Settings().mailer == MailerName.RESEND


def test_a_mailer_that_does_not_exist_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MARKETING_OS_MAILER", "sendgrid")

    with pytest.raises(ConfigError, match="MARKETING_OS_MAILER"):
        Settings()


def test_the_resend_key_and_sender_are_absent_until_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MARKETING_OS_RESEND_API_KEY", raising=False)
    monkeypatch.delenv("MARKETING_OS_MAIL_FROM", raising=False)

    settings = Settings()

    assert settings.resend_api_key is None
    assert settings.mail_from is None


def test_the_resend_key_and_sender_are_read_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MARKETING_OS_RESEND_API_KEY", "re_123")
    monkeypatch.setenv("MARKETING_OS_MAIL_FROM", "We-OS <hello@we-os.example>")

    settings = Settings()

    assert settings.resend_api_key == "re_123"
    assert settings.mail_from == "We-OS <hello@we-os.example>"


def test_the_app_url_defaults_to_the_local_web_app(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MARKETING_OS_APP_URL", raising=False)

    assert Settings().app_url == "http://localhost:3000"


def test_the_app_url_is_read_without_its_trailing_slash(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MARKETING_OS_APP_URL", "https://app.we-os.example/")

    assert Settings().app_url == "https://app.we-os.example"


# --- Building the mailer ---------------------------------------------------------


def test_the_no_op_mailer_is_built_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MARKETING_OS_MAILER", raising=False)
    monkeypatch.delenv("MARKETING_OS_RESEND_API_KEY", raising=False)

    mailer = build_mailer(Settings())

    assert isinstance(mailer, NoopMailer)
    assert isinstance(mailer, Mailer)


def test_resend_is_built_only_when_selected_with_a_key_and_a_sender(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MARKETING_OS_MAILER", "resend")
    monkeypatch.setenv("MARKETING_OS_RESEND_API_KEY", "re_123")
    monkeypatch.setenv("MARKETING_OS_MAIL_FROM", "We-OS <hello@we-os.example>")

    assert isinstance(build_mailer(Settings()), ResendMailer)


def test_selecting_resend_without_a_key_is_refused_by_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MARKETING_OS_MAILER", "resend")
    monkeypatch.delenv("MARKETING_OS_RESEND_API_KEY", raising=False)
    monkeypatch.setenv("MARKETING_OS_MAIL_FROM", "We-OS <hello@we-os.example>")

    with pytest.raises(ConfigError, match="MARKETING_OS_RESEND_API_KEY"):
        build_mailer(Settings())


def test_selecting_resend_without_a_sender_is_refused_by_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MARKETING_OS_MAILER", "resend")
    monkeypatch.setenv("MARKETING_OS_RESEND_API_KEY", "re_123")
    monkeypatch.delenv("MARKETING_OS_MAIL_FROM", raising=False)

    with pytest.raises(ConfigError, match="MARKETING_OS_MAIL_FROM"):
        build_mailer(Settings())


# --- The mailers ----------------------------------------------------------------


def test_the_no_op_mailer_sends_nothing_and_says_so(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="marketing_os.mail"):
        NoopMailer().send(MESSAGE)

    assert "sam@coastcoffee.example" in caplog.text
    assert "Your Brand DNA is due a review" in caplog.text


def _resend(handler: object) -> ResendMailer:
    """Build a Resend mailer over a faked transport.

    Args:
        handler: The ``httpx.MockTransport`` handler answering the request.

    Returns:
        The mailer, sending as We-OS.
    """
    return ResendMailer(
        "re_123",
        sender="We-OS <hello@we-os.example>",
        client=httpx.Client(transport=httpx.MockTransport(handler)),  # type: ignore[arg-type]
    )


def test_resend_is_asked_to_send_the_message_from_the_configured_sender() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"id": "email_1"})

    _resend(handler).send(MESSAGE)

    assert len(seen) == 1
    assert seen[0].url == "https://api.resend.com/emails"
    assert seen[0].headers["Authorization"] == "Bearer re_123"
    assert json.loads(seen[0].content) == {
        "from": "We-OS <hello@we-os.example>",
        "to": ["sam@coastcoffee.example"],
        "subject": "Your Brand DNA is due a review",
        "text": "Take a look at https://app.we-os.example/brand",
    }


def test_a_rejected_resend_key_is_a_configuration_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "API key is invalid"})

    with pytest.raises(ConfigError, match="MARKETING_OS_RESEND_API_KEY"):
        _resend(handler).send(MESSAGE)


def test_a_failed_send_is_reported_with_what_resend_said() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"message": "The from address is not verified"})

    with pytest.raises(ToolError, match="not verified"):
        _resend(handler).send(MESSAGE)


def test_a_network_failure_is_reported_as_a_failed_send() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route to host")

    with pytest.raises(ToolError, match="Resend"):
        _resend(handler).send(MESSAGE)


# --- Whether a reminder is due, as a pure function ------------------------------


def test_a_due_review_never_reminded_about_is_due_a_reminder() -> None:
    review = DnaReview(reviewed_at=T0 - WEEK - timedelta(days=1), due=True)

    assert reminder_due(review, reminded_at=None, now=T0, interval=WEEK) is True


def test_a_review_that_is_not_due_gets_no_reminder_however_long_ago_the_last_was() -> None:
    review = DnaReview(reviewed_at=T0, due=False)

    assert reminder_due(review, reminded_at=T0 - 5 * WEEK, now=T0, interval=WEEK) is False


def test_a_reminder_within_the_period_is_not_sent_again() -> None:
    review = DnaReview(reviewed_at=T0 - 3 * WEEK, due=True)

    assert reminder_due(review, reminded_at=T0 - WEEK, now=T0, interval=WEEK) is False
    assert (
        reminder_due(review, reminded_at=T0 - WEEK - timedelta(seconds=1), now=T0, interval=WEEK)
        is True
    )


# --- One tick ---------------------------------------------------------------------


class FakeMailer:
    """A mailer that keeps what it was asked to send.

    Attributes:
        sent: Every message, in order.
        refuse: Addresses whose messages fail to send, for the failure cases.
    """

    def __init__(self) -> None:
        """Start with nothing sent."""
        self.sent: list[EmailMessage] = []
        self.refuse: set[str] = set()

    def send(self, message: EmailMessage) -> None:
        """Keep the message, or refuse it.

        Args:
            message: The message to send.

        Raises:
            ToolError: If the address is one this mailer refuses.
        """
        if message.to in self.refuse:
            raise ToolError(f"refused {message.to}")
        self.sent.append(message)


class Businesses:
    """The stores a tick reads, and a hand-moved clock.

    Attributes:
        tenants: The minting directory the businesses are registered in.
        answers: Their Brand DNA answers.
        questionnaires: The published question set.
        mailer: The mailer the tick sends through.
        now: The instant the next tick runs at.
    """

    def __init__(self) -> None:
        """Start empty, at T0."""
        self.tenants = InMemoryTenantDirectory()
        self.answers = InMemoryAnswerStore()
        self.questionnaires = InMemoryQuestionnaireStore()
        self.mailer = FakeMailer()
        self.now = T0

    def register(
        self,
        organization: str,
        *,
        name: str,
        email: str | None,
        reviewed_at: datetime | None,
        complete: bool = True,
    ) -> str:
        """Register a business with a Brand DNA and a recorded review.

        Args:
            organization: The IdP organization id.
            name: The business name.
            email: The signed-in email, or ``None`` for a business no one has
                signed in to since the address was recorded.
            reviewed_at: When it last reviewed its DNA, or ``None`` if never.
            complete: Whether every Required question is answered.

        Returns:
            The platform tenant id.
        """
        tenant = self.tenants.resolve(external_auth_id=organization, name=name, email=email)
        questions = SEED_QUESTIONNAIRE.required_questions
        answered = questions if complete else questions[:1]
        self.answers.upsert(
            tenant.tenant_id,
            version=SEED_QUESTIONNAIRE.version,
            answers=[DnaAnswer(question_id=q.id, answer=f"Answer to {q.field}") for q in answered],
        )
        if reviewed_at is not None:
            self.tenants.mark_dna_reviewed(tenant.tenant_id, at=reviewed_at)
        return tenant.tenant_id

    def tick(self) -> list[str]:
        """Run one tick at ``now``.

        Returns:
            The addresses reminded this tick.
        """
        sent = send_due_reminders(
            tenants=self.tenants,
            answers=self.answers,
            questionnaires=self.questionnaires,
            mailer=self.mailer,
            now=self.now,
            interval=WEEK,
            app_url=APP_URL,
        )
        return [reminder.to for reminder in sent]


@pytest.fixture
def businesses() -> Businesses:
    """Return three businesses: one due, one recently reviewed, one with no DNA."""
    world = Businesses()
    world.register(
        "org_due", name="Coast Coffee", email="sam@coastcoffee.example", reviewed_at=T0 - 2 * WEEK
    )
    world.register(
        "org_fresh", name="Fresh Bakes", email="ana@freshbakes.example", reviewed_at=T0 - WEEK / 2
    )
    world.register(
        "org_new",
        name="New Gym",
        email="lee@newgym.example",
        reviewed_at=T0 - 2 * WEEK,
        complete=False,
    )
    return world


def test_one_tick_reminds_each_due_business_once_and_no_one_else(businesses: Businesses) -> None:
    reminded = businesses.tick()

    assert reminded == ["sam@coastcoffee.example"]
    assert [message.to for message in businesses.mailer.sent] == ["sam@coastcoffee.example"]


def test_the_reminder_names_the_business_and_links_to_the_brand_page(
    businesses: Businesses,
) -> None:
    businesses.tick()

    [message] = businesses.mailer.sent
    assert message.subject == "Your Brand DNA is due a review"
    assert "Coast Coffee" in message.text
    assert f"{APP_URL}/brand" in message.text


def test_a_second_tick_within_the_period_sends_nothing(businesses: Businesses) -> None:
    businesses.tick()
    businesses.now += timedelta(days=1)

    assert businesses.tick() == []
    businesses.now += timedelta(days=2)
    assert businesses.tick() == []


def test_a_tick_after_the_period_reminds_again(businesses: Businesses) -> None:
    """A week on, the untouched review is mentioned once more — and Fresh Bakes is due by then."""
    businesses.tick()
    businesses.now += WEEK + timedelta(seconds=1)

    assert sorted(businesses.tick()) == ["ana@freshbakes.example", "sam@coastcoffee.example"]
    assert [m.to for m in businesses.mailer.sent].count("sam@coastcoffee.example") == 2


def test_a_business_that_reviews_before_the_next_period_is_not_reminded() -> None:
    world = Businesses()
    due = world.register(
        "org_due", name="Coast Coffee", email="sam@coastcoffee.example", reviewed_at=T0 - 2 * WEEK
    )
    world.tick()
    world.now += timedelta(days=1)
    world.tenants.mark_dna_reviewed(due, at=world.now)
    world.now += WEEK

    assert world.tick() == []
    world.now += timedelta(days=1)
    assert world.tick() == ["sam@coastcoffee.example"]


def test_a_business_becoming_due_later_is_reminded_then(businesses: Businesses) -> None:
    businesses.tick()
    businesses.now += WEEK / 2 + timedelta(seconds=1)

    assert businesses.tick() == ["ana@freshbakes.example"]


def test_a_due_business_with_no_address_is_skipped_until_one_is_known(
    caplog: pytest.LogCaptureFixture,
) -> None:
    world = Businesses()
    world.register("org_quiet", name="Quiet Books", email=None, reviewed_at=T0 - 2 * WEEK)

    with caplog.at_level(logging.INFO, logger="marketing_os.reminders"):
        assert world.tick() == []
    assert "no address" in caplog.text
    world.tenants.resolve(
        external_auth_id="org_quiet", name="Quiet Books", email="kim@quietbooks.example"
    )
    assert world.tick() == ["kim@quietbooks.example"]


def test_one_failed_send_is_logged_and_the_rest_are_still_sent(
    caplog: pytest.LogCaptureFixture,
) -> None:
    world = Businesses()
    world.register("org_a", name="A", email="a@a.example", reviewed_at=T0 - 2 * WEEK)
    world.register("org_b", name="B", email="b@b.example", reviewed_at=T0 - 2 * WEEK)
    world.mailer.refuse.add("a@a.example")

    with caplog.at_level(logging.WARNING, logger="marketing_os.reminders"):
        assert world.tick() == ["b@b.example"]
    assert "a@a.example" in caplog.text
    world.mailer.refuse.clear()
    assert world.tick() == ["a@a.example"]


def test_a_reminder_is_recorded_on_the_business(businesses: Businesses) -> None:
    businesses.tick()

    by_name = {tenant.name: tenant for tenant in businesses.tenants.all()}
    assert by_name["Coast Coffee"].dna_reminded_at == T0
    assert by_name["Fresh Bakes"].dna_reminded_at is None


# --- The loop ---------------------------------------------------------------------


async def test_the_loop_ticks_at_once_then_keeps_going_past_a_failure(
    caplog: pytest.LogCaptureFixture,
) -> None:
    ticks: list[int] = []

    def tick() -> None:
        ticks.append(len(ticks))
        if len(ticks) == 1:
            raise RuntimeError("the database blinked")

    with caplog.at_level(logging.ERROR, logger="marketing_os.reminders"):
        task = asyncio.create_task(remind_on_interval(tick, timedelta(milliseconds=10)))
        for _ in range(200):
            if len(ticks) >= 3:
                break
            await asyncio.sleep(0.01)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    assert len(ticks) >= 3
    assert "the database blinked" in caplog.text
    assert task.cancelled()


# --- With the API -----------------------------------------------------------------


@pytest.fixture
def api_env(repo: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Point the API at the hermetic repo and the prototype adapters, and clean up after.

    Args:
        repo: The hermetic repository root fixture.
        monkeypatch: The pytest monkeypatch fixture.

    Yields:
        Nothing; the environment is set for the test's duration.
    """
    monkeypatch.setenv("MARKETING_OS_ROOT", str(repo))
    monkeypatch.setenv("MARKETING_OS_DNA_REVIEW_INTERVAL", "7d")
    import marketing_os.entrypoints.api.app as api_module

    api_module.get_settings.cache_clear()
    install_prototype_adapters(repo)
    yield
    api_module.app.dependency_overrides.clear()
    api_module.get_settings.cache_clear()
    clear_prototype_adapters()


def test_the_app_starts_without_a_resend_key_on_the_no_op_mailer(
    api_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("MARKETING_OS_MAILER", raising=False)
    monkeypatch.delenv("MARKETING_OS_RESEND_API_KEY", raising=False)
    import marketing_os.entrypoints.api.app as api_module

    with TestClient(api_module.app) as client:
        assert client.get("/health").status_code == 200


def test_selecting_resend_without_a_key_stops_the_app_at_startup(
    api_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MARKETING_OS_MAILER", "resend")
    monkeypatch.delenv("MARKETING_OS_RESEND_API_KEY", raising=False)
    monkeypatch.setenv("MARKETING_OS_MAIL_FROM", "We-OS <hello@we-os.example>")
    import marketing_os.entrypoints.api.app as api_module

    with pytest.raises(ConfigError, match="MARKETING_OS_RESEND_API_KEY"):
        with TestClient(api_module.app):
            pass


def test_the_reminder_task_starts_with_the_api_and_reminds_a_due_business(
    api_env: None, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """The loop's first tick runs at startup, through the no-op mailer, and says so in the log."""
    monkeypatch.delenv("MARKETING_OS_MAILER", raising=False)
    import marketing_os.entrypoints.api.app as api_module

    world = Businesses()
    world.register(
        "org_due", name="Coast Coffee", email="sam@coastcoffee.example", reviewed_at=T0 - 2 * WEEK
    )
    monkeypatch.setattr(api_module, "get_tenant_directory", lambda: world.tenants)
    monkeypatch.setattr(api_module, "get_answer_store", lambda: world.answers)
    monkeypatch.setattr(api_module, "get_questionnaire_store", lambda: world.questionnaires)
    monkeypatch.setattr(api_module, "get_clock", lambda: lambda: T0)

    with caplog.at_level(logging.INFO, logger="marketing_os"):
        with TestClient(api_module.app) as client:
            assert client.get("/health").status_code == 200
            for _ in range(200):
                if world.tenants.all()[0].dna_reminded_at is not None:
                    break
                time.sleep(0.01)

    [tenant] = world.tenants.all()
    assert tenant.dna_reminded_at == T0
    assert "mail.noop to=sam@coastcoffee.example" in caplog.text
    assert "reminder.sent" in caplog.text

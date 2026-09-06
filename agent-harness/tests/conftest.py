"""Shared test fixtures: scripted fakes, a hermetic temp repo, and Postgres.

Everything here is offline by default. The Postgres fixtures are the exception
and they opt in rather than out: they skip unless ``MARKETING_OS_TEST_POSTGRES=1``
is set, so the fast suite runs with no Docker and no database, and the same
conformance assertions run against a real containerised server when asked.
"""

from __future__ import annotations

import asyncio
import os
import re
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

from marketing_os.config import Settings
from marketing_os.questionnaire import SEED_QUESTIONNAIRE, render_brand_dna
from marketing_os.schemas import (
    BrandDnaRecord,
    Discrepancy,
    DnaAnswer,
    ReviewVerdict,
    VerifiedIdentity,
)

Handler = Callable[[list[BaseMessage], int], AIMessage]

"""A tenant id and a campaign slug are distinct things, so the fixtures use
different strings for them — sharing one string would hide code that confuses
the two."""

TENANT = "org_acme"
OTHER_TENANT = "org_rival"
SLUG = "acme"

PLACEHOLDER_DNA = "# Brand DNA — Acme\n\n## Business\n- **Business name:** <name>\n"

COMPLETE_GOAL_BODY: dict[str, object] = {
    "name": "Spring Refill Push",
    "objective": "120 refill subscriptions in 8 weeks",
    "timeframe": {"start_date": "2026-09-01", "end_date": "2026-10-27"},
    "budget": {"amount": 4000, "currency": "SGD"},
    "audience_segment": "Urban 22-35 beginners curious about climbing",
    "kpis": {
        "business": "120 refill subscriptions",
        "marketing": "2.5% landing-page conversion",
        "creative": "30% hook rate on launch video",
    },
}
"""A complete ``POST /campaigns`` body, matching the segment the filled Brand DNA
fixture names — a campaign may only target a segment the business described."""


def identity_for(tenant: str = TENANT, user: str | None = None) -> VerifiedIdentity:
    """Build a verified identity for a person at a tenant, as the auth dependency would.

    Args:
        tenant: The tenant the caller acts for.
        user: The signed-in person; defaults to that tenant's owner. Pass a
            second value to act as a colleague at the same business, which is
            what the one-campaign-one-person guard is about.

    Returns:
        A :class:`VerifiedIdentity` suitable for overriding ``get_identity``.
    """
    return VerifiedIdentity(
        user_id=user or f"usr_{tenant}",
        tenant_id=tenant,
        organization_id=f"org_idp_{tenant}",
        email=f"owner@{tenant}.example",
        business_name="Acme Climbing Gym",
    )


def authenticate(app: Any, tenant: str = TENANT, user: str | None = None) -> None:
    """Override the API's auth dependency to act as a verified person at a tenant.

    Mirrors what a real bearer token would produce, so no test contacts a live
    IdP while still exercising every tenant-scoping path behind the dependency.

    Args:
        app: The FastAPI application to override.
        tenant: The tenant the overridden identity acts for.
        user: The signed-in person; defaults to that tenant's owner.
    """
    from marketing_os.entrypoints.api.app import get_identity

    app.dependency_overrides[get_identity] = lambda: identity_for(tenant, user)


class PrototypeBackend:
    """The filesystem and in-memory adapters, as one storage backend.

    Production runs on Postgres only: with no DSN configured the real backend
    raises rather than falling back to local disk, so a test wanting the
    prototype adapters installs this one out loud. It holds no connection, so
    ``open`` and ``close`` are no-ops.

    Every adapter is built once and held, because a test that writes through one
    getter and reads through another must see the same store.
    """

    def __init__(self, root: Path) -> None:
        """Build the full set of adapters over a hermetic repo.

        Args:
            root: The repository root the filesystem adapters are rooted at.
        """
        from langgraph.checkpoint.memory import MemorySaver

        from marketing_os.adapters.deliverables import FilesystemDeliverableStore
        from marketing_os.adapters.documents import FilesystemDocumentStore
        from marketing_os.adapters.questionnaire import (
            InMemoryAnswerStore,
            InMemoryQuestionnaireStore,
        )
        from marketing_os.adapters.runs import InMemoryRunStore
        from marketing_os.adapters.tenants import PassthroughTenantDirectory
        from marketing_os.adapters.usage import InMemoryUsageLedger

        self.documents = FilesystemDocumentStore(root)
        self.deliverables = FilesystemDeliverableStore(root)
        self.tenants = PassthroughTenantDirectory()
        self.runs = InMemoryRunStore()
        self.questionnaires = InMemoryQuestionnaireStore()
        self.answers = InMemoryAnswerStore()
        self.usage = InMemoryUsageLedger(Settings(root=root))
        self.checkpointer = MemorySaver()

    async def open(self) -> None:
        """Do nothing: these adapters hold no connection."""

    async def close(self) -> None:
        """Do nothing: these adapters hold no connection."""


def install_prototype_adapters(root: Path) -> None:
    """Point the API at the filesystem and in-memory adapters for a hermetic test.

    Nothing selects them implicitly, which is the point — a misconfigured deploy
    fails loudly instead of writing a business's campaigns to a container's
    filesystem — so a test that wants them says so.

    Args:
        root: The hermetic repository root the filesystem adapters are rooted at.
    """
    from marketing_os.entrypoints.api.app import use_backend

    use_backend(PrototypeBackend(root))


def prototype_adapters(root: Path) -> dict[str, Any]:
    """Return the storage arguments a graph builder or the runner now requires.

    The builders and ``arun_campaign`` take their stores as required keyword
    arguments, so nothing picks a storage backend on a caller's behalf. A test
    driving them against the hermetic repo therefore names the filesystem
    adapters here rather than repeating them at every call site.

    ``usage_ledger`` and ``checkpointer`` are supplied as ``None``, which stays a
    legal value with a stated meaning: uncharged (ADR-0020), and in-memory and
    non-resumable respectively.

    Args:
        root: The hermetic repository root the filesystem adapters are rooted at.

    Returns:
        The keyword arguments to splat into the builder or runner call.
    """
    from marketing_os.adapters.deliverables import FilesystemDeliverableStore
    from marketing_os.adapters.documents import FilesystemDocumentStore

    return {
        "document_store": FilesystemDocumentStore(root),
        "deliverable_store": FilesystemDeliverableStore(root),
        "usage_ledger": None,
        "checkpointer": None,
    }


def with_prototype_defaults(settings: Settings, kwargs: dict[str, Any]) -> dict[str, Any]:
    """Fill in the storage arguments a builder requires, leaving any given ones alone.

    Args:
        settings: The harness settings naming the hermetic repo root.
        kwargs: The builder's keyword arguments, modified in place.

    Returns:
        The same mapping, with every unset storage argument defaulted.
    """
    for keyword, adapter in prototype_adapters(settings.root).items():
        kwargs.setdefault(keyword, adapter)
    return kwargs


def clear_prototype_adapters() -> None:
    """Put the API back on the backend its configuration selects.

    Called on teardown so a hermetic filesystem store cannot leak into the next
    test and hide a case that should have failed for want of a database.
    """
    from marketing_os.entrypoints.api.app import use_backend

    use_backend(None)


def run_without_approval_gates(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set every stage's approval policy to ``auto`` for this test.

    The approval policy is data (ADR-0015), so a test about pipeline traversal
    turns the gates off through the same configuration lever an operator would,
    rather than through a code path only tests can reach. An empty value means
    "no stage is gated", which is distinct from the variable being unset.

    Args:
        monkeypatch: The pytest monkeypatch fixture.
    """
    monkeypatch.setenv("MARKETING_OS_HUMAN_GATES", "")


PASS_VERDICT = ReviewVerdict(passed=True, summary="ok")
FAIL_VERDICT = ReviewVerdict(
    passed=False,
    summary="needs work",
    discrepancies=[Discrepancy(rubric_point="x", problem="p", fix="f")],
)


class ProgrammableChatModel(BaseChatModel):
    """A scripted chat model whose replies are produced by a handler callable.

    The handler receives the current message list and the zero-based index of the
    model call, so a test can make the model write a deliverable, refuse to, or
    revise based on the conversation so far. No network is used.
    """

    handler: Handler
    calls: list[int] = Field(default_factory=list)
    model_config = {"arbitrary_types_allowed": True}

    @property
    def _llm_type(self) -> str:
        """Return the model type identifier."""
        return "programmable"

    def bind_tools(self, tools: Any, **kwargs: Any) -> ProgrammableChatModel:
        """Ignore tool binding and return self, since replies are scripted.

        Args:
            tools: The tools being bound (ignored).
            **kwargs: Additional binding arguments (ignored).

        Returns:
            This model instance.
        """
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Produce the next scripted reply.

        Args:
            messages: The conversation so far.
            stop: Stop sequences (ignored).
            run_manager: The callback manager (ignored).
            **kwargs: Additional arguments (ignored).

        Returns:
            A chat result wrapping the handler's message.
        """
        index = len(self.calls)
        self.calls.append(1)
        message = self.handler(list(messages), index)
        return ChatResult(generations=[ChatGeneration(message=message)])


class BlockingChatModel(BaseChatModel):
    """An async-only chat model whose ``ainvoke`` blocks until the task is cancelled.

    It signals when the LLM call is in-flight via :attr:`entered` and records
    whether that awaited call was cancelled via :attr:`was_cancelled`. Used to hold
    a run open (blocked inside the specialist's awaited LLM call) so cancellation
    and per-slug concurrency can be observed without any network: the run stays
    active in the registry until its task is cancelled, at which point the awaited
    call is aborted.
    """

    entered: asyncio.Event = Field(default_factory=asyncio.Event)
    was_cancelled: bool = False
    model_config = {"arbitrary_types_allowed": True}

    @property
    def _llm_type(self) -> str:
        """Return the model type identifier."""
        return "blocking"

    def bind_tools(self, tools: Any, **kwargs: Any) -> BlockingChatModel:
        """Ignore tool binding and return self, since the reply never arrives.

        Args:
            tools: The tools being bound (ignored).
            **kwargs: Additional binding arguments (ignored).

        Returns:
            This model instance.
        """
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Fail loudly if invoked synchronously; this model is async-only.

        Args:
            messages: The conversation so far (unused).
            stop: Stop sequences (ignored).
            run_manager: The callback manager (ignored).
            **kwargs: Additional arguments (ignored).

        Raises:
            NotImplementedError: Always, to prove the async path is exercised.
        """
        raise NotImplementedError("blocking model is async-only")

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Signal that the LLM call is in-flight, then block until cancelled.

        Args:
            messages: The conversation so far (unused).
            stop: Stop sequences (ignored).
            run_manager: The callback manager (ignored).
            **kwargs: Additional arguments (ignored).

        Returns:
            A chat result — never reached, since the call blocks forever.

        Raises:
            asyncio.CancelledError: When the run's task is cancelled mid-call.
        """
        self.entered.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.was_cancelled = True
            raise
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="unreachable"))])


def write_call(path: str, content: str, call_id: str = "call_write") -> AIMessage:
    """Build an assistant message that calls the ``write_file`` tool.

    Args:
        path: The deliverable path to write.
        content: The deliverable content.
        call_id: The tool-call id.

    Returns:
        An ``AIMessage`` carrying a single ``write_file`` tool call.
    """
    return AIMessage(
        content="",
        tool_calls=[
            {"name": "write_file", "args": {"path": path, "content": content}, "id": call_id}
        ],
    )


def read_call(path: str, call_id: str = "call_read") -> AIMessage:
    """Build an assistant message that calls the ``read_file`` tool.

    Args:
        path: The path to read.
        call_id: The tool-call id.

    Returns:
        An ``AIMessage`` carrying a single ``read_file`` tool call.
    """
    return AIMessage(
        content="",
        tool_calls=[{"name": "read_file", "args": {"path": path}, "id": call_id}],
    )


class FakeReviewer:
    """A reviewer that returns a scripted sequence of verdicts.

    The final verdict repeats once the script is exhausted so revise loops that
    eventually pass are easy to express.
    """

    def __init__(self, verdicts: list[ReviewVerdict]) -> None:
        """Initialise the fake reviewer.

        Args:
            verdicts: The verdicts to return in order.
        """
        self._verdicts = list(verdicts)
        self.calls: list[tuple[str, str]] = []

    async def areview(self, stage_key: str, deliverable_text: str) -> ReviewVerdict:
        """Return the next scripted verdict.

        Args:
            stage_key: The stage being reviewed.
            deliverable_text: The deliverable text (recorded for assertions).

        Returns:
            The next scripted verdict, or the last one once exhausted.
        """
        self.calls.append((stage_key, deliverable_text))
        if len(self._verdicts) > 1:
            return self._verdicts.pop(0)
        return self._verdicts[0]


_DNA_TEMPLATE = """\
# Brand DNA — <CUSTOMER NAME>

## Required (the agent will not start without these)

### Business
- **Business name:** <name>
- **What they sell:** <products/services>

### Customers
- **Primary segment(s):** <who buys>

### Differentiation
- **Why customers choose them over alternatives:** <reason>

## Recommended

- **Competitors:** <who>
"""

_GOAL_TEMPLATE = """\
# Campaign Goal — <CAMPAIGN NAME>

## Required

- **Primary business objective:** <outcome>
- **Timeframe:** <start → end>
- **Campaign budget:** <spend available>
- **Target segment for this campaign:** <which DNA segment>

### Success metrics (define all three tiers)
- **Business KPI:** <target>
- **Marketing KPI:** <target>
- **Creative KPI:** <target>

## Optional

- **Offer / promotion:** <if any>
"""

"""The Brand DNA a business has after completing onboarding: the rendered
projection of a complete set of answers to the published question set. Building
it from the seed rather than hand-writing it is deliberate — the gate derives
its Required fields from that same set (ADR-0018), so a hand-written fixture
would drift out of the gate the moment a question was added."""


def filled_dna_answers() -> BrandDnaRecord:
    """Answer every Required question in the seed set, as an onboarded business has.

    Returns:
        A complete Brand DNA record at the seed questionnaire's version.
    """
    written = {
        "q_business_name": "Acme Climbing Gym",
        "q_what_they_sell": "Monthly bouldering memberships and intro classes",
        "q_category": "Boutique fitness — indoor bouldering",
        "q_price_point": "$90 a month, $25 for an intro class",
        "q_segments": "Urban 22-35 beginners curious about climbing",
        "q_pain_points": "Gyms are boring and they do not know how to start climbing",
        "q_why_chosen": "Only gym in the city with free coached intro sessions",
        "q_geography": "Inner-city Melbourne, 10km radius",
        "q_languages": "English",
        "q_budget_range": "$3,000 a month including ad spend",
        "q_hard_constraints": "No injury or fitness-outcome claims",
        "q_competitors": "BigBox Fitness, two independent gyms",
    }
    return BrandDnaRecord(
        questionnaire_version=SEED_QUESTIONNAIRE.version,
        updated_at="2026-09-01T10:00:00Z",
        answers=[
            DnaAnswer(question_id=question_id, answer=answer)
            for question_id, answer in written.items()
        ],
    )


_DNA_FILLED = render_brand_dna(
    SEED_QUESTIONNAIRE, filled_dna_answers(), business_name="Acme Climbing Gym"
)

_GOAL_FILLED = """\
# Campaign Goal — Acme Spring

## Required
- **Primary business objective:** +40 new memberships in 8 weeks
- **Timeframe:** 2026-09-01 → 2026-10-27
- **Campaign budget:** 4000 AUD
- **Target segment for this campaign:** Urban 22-35 beginners curious about climbing

### Success metrics (define all three tiers)
- **Business KPI:** 40 memberships
- **Marketing KPI:** 3% landing-page conversion
- **Creative KPI:** 25% hook rate on intro video

## Optional
- **Offer / promotion:** First month half price
"""

_AGENT_MD = """\
---
name: market-research
description: Produces research findings only.
tools: Read, Grep, Glob, Write, WebSearch, WebFetch
---

You are the **Market Research Agent**. Output research findings only.
"""

_RULES_MD = """\
# Operating Principles

1. Strategy before content.
2. Every recommendation explains why and ties to a business objective.
"""


def _write(path: Path, text: str) -> None:
    """Write text to a path, creating parent directories.

    Args:
        path: The destination path.
        text: The content to write.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture(autouse=True)
def _isolate_from_developer_env(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stop a developer's real ``.env`` from leaking into the suite.

    The entrypoints call :func:`load_env` at startup, which walks up from the
    working directory and loads whatever ``.env`` it finds. Left alone, a test
    asserting that an unset variable is an error passes or fails depending on
    whose machine it runs on — which is how a real ``.env`` first broke the
    CLI's missing-tenant test.

    Tests of ``load_env`` itself opt out with ``@pytest.mark.uses_real_dotenv``.

    Args:
        request: The pytest request, used to honour the opt-out marker.
        monkeypatch: The pytest monkeypatch fixture.
    """
    if request.node.get_closest_marker("uses_real_dotenv"):
        return
    monkeypatch.setattr("marketing_os.entrypoints.env.load_dotenv", lambda *args, **kwargs: False)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Create a minimal Marketing OS repo with a valid DNA and goal for one tenant.

    Tenant-owned documents live under ``tenants/<tenant>/``; everything else in
    the tree is code-shipped material the read sandbox serves.

    Args:
        tmp_path: The pytest temporary directory.

    Returns:
        The repository root path.
    """
    _write(tmp_path / ".claude" / "agents" / "market-research.md", _AGENT_MD)
    _write(tmp_path / ".claude" / "rules" / "operating-principles.md", _RULES_MD)
    _write(tmp_path / "templates" / "brand-dna.md", _DNA_TEMPLATE)
    _write(tmp_path / "templates" / "campaign-goal.md", _GOAL_TEMPLATE)
    _write(tmp_path / "tenants" / TENANT / "dna.md", _DNA_FILLED)
    _write(tmp_path / "tenants" / TENANT / "campaigns" / SLUG / "goal.md", _GOAL_FILLED)
    _write(tmp_path / "guardrails" / "shared.md", "- DNA-grounded.\n- Explains why.\n")
    _write(tmp_path / "guardrails" / "research.md", "- Covers customer/competitor/market.\n")
    return tmp_path


@pytest.fixture
def settings(repo: Path) -> Settings:
    """Build validated settings rooted at the hermetic repo.

    Args:
        repo: The repository root fixture.

    Returns:
        The validated settings.
    """
    built = Settings(root=repo)
    built.validate_root()
    return built


_PIPELINE_AGENTS = {
    "brand-strategy": "You are the Brand Strategy Agent.",
    "creative-director": "You are the Creative Director Agent.",
    "creative-asset-prompt": "You are the Creative Asset Prompt Agent.",
    "performance-marketing": "You are the Performance Marketing Agent.",
}


def write_all_agent_specs(settings: Settings) -> None:
    """Write the downstream specialist specs so a full pipeline run can build.

    The ``repo`` fixture ships only ``market-research.md``; the remaining stages
    need their agent markdown present before the campaign graph can be assembled.

    Args:
        settings: The harness settings locating the agents directory.
    """
    for name, body in _PIPELINE_AGENTS.items():
        path = settings.agents_dir / f"{name}.md"
        path.write_text(
            f"---\nname: {name}\ndescription: {name}\ntools: Read, Grep, Glob, Write\n---\n{body}",
            encoding="utf-8",
        )


def deliverable_from(messages: list[BaseMessage]) -> str:
    """Extract the ``campaigns/*.md`` deliverable path named in the seeded task.

    Args:
        messages: The conversation so far.

    Returns:
        The last ``campaigns/<slug>/<name>.md`` path found in the messages.
    """
    text = "\n".join(str(m.content) for m in messages)
    matches = re.findall(r"campaigns/[\w-]+/[\w-]+\.md", text)
    assert matches, "no deliverable path in task"
    return matches[-1]


def writing_handler(messages: list[BaseMessage], index: int) -> AIMessage:
    """Write the deliverable named in the task, then stop once the tool has run.

    Args:
        messages: The conversation so far.
        index: The model-call index (unused).

    Returns:
        A ``write_file`` tool call, or a plain completion after the write.
    """
    if isinstance(messages[-1], ToolMessage):
        return AIMessage(content="Saved. Done.")
    path = deliverable_from(messages)
    return write_call(path, f"# Deliverable\n\nContent for {path}.")


def install_scripted_graph(
    monkeypatch: pytest.MonkeyPatch,
    *,
    handler: Handler = writing_handler,
    verdicts: list[ReviewVerdict] | None = None,
    model_factory: Callable[[], BaseChatModel] | None = None,
) -> None:
    """Patch the runner's graph builders to inject a scripted model and reviewer.

    The API entrypoint builds the graph internally through the runner, so it
    never exposes a model seam. This wraps :func:`build_campaign_graph` and
    :func:`build_single_stage_graph` as the runner imports them, defaulting the
    ``model`` and ``reviewer`` arguments to hermetic fakes so no network is used,
    the ``questionnaire`` argument to the code-shipped seed set, which is what an
    unconfigured deployment serves, and the storage arguments to the hermetic
    repo's filesystem adapters — the builders require those (nothing picks a
    storage backend implicitly), and a caller that supplies its own still wins.

    Args:
        monkeypatch: The pytest monkeypatch fixture.
        handler: The scripted chat-model handler for the default model.
        verdicts: The reviewer verdict script; defaults to a single pass.
        model_factory: A factory returning the chat model to inject per graph
            build; defaults to a :class:`ProgrammableChatModel` driven by
            ``handler``. Supply a factory (e.g. returning a :class:`BlockingChatModel`)
            to hold runs open for concurrency and cancellation tests.
    """
    from marketing_os.graph import graph as graph_mod
    from marketing_os.graph import runner as runner_mod

    script = list(verdicts) if verdicts else [PASS_VERDICT]
    build_model = model_factory or (lambda: ProgrammableChatModel(handler=handler))
    real_campaign = graph_mod.build_campaign_graph
    real_single = graph_mod.build_single_stage_graph

    def defaults(settings: Settings, kwargs: dict[str, Any]) -> dict[str, Any]:
        kwargs.setdefault("model", build_model())
        kwargs.setdefault("reviewer", FakeReviewer(list(script)))
        kwargs.setdefault("questionnaire", SEED_QUESTIONNAIRE)
        return with_prototype_defaults(settings, kwargs)

    def campaign(settings: Settings, **kwargs: Any) -> Any:
        return real_campaign(settings, **defaults(settings, kwargs))

    def single(settings: Settings, stage_key: str, **kwargs: Any) -> Any:
        return real_single(settings, stage_key, **defaults(settings, kwargs))

    monkeypatch.setattr(runner_mod, "build_campaign_graph", campaign)
    monkeypatch.setattr(runner_mod, "build_single_stage_graph", single)


POSTGRES_IMAGE = "postgres:16-alpine"

APP_ROLE = "marketing_os_app"
APP_PASSWORD = "marketing_os_app"

_CREATE_APP_ROLE = f"""
DO $$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{APP_ROLE}') THEN
        CREATE ROLE {APP_ROLE} LOGIN PASSWORD '{APP_PASSWORD}';
    END IF;
END $$;
"""


def _with_credentials(dsn: str, user: str, password: str) -> str:
    """Return a connection string pointing at the same database as another user.

    Args:
        dsn: The connection string to rewrite.
        user: The role to connect as.
        password: That role's password.

    Returns:
        The rewritten connection string.
    """
    parts = urlsplit(dsn)
    netloc = f"{user}:{password}@{parts.hostname}:{parts.port}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


@pytest.fixture(scope="session")
def postgres_superuser_dsn() -> Iterator[str]:
    """Start a Postgres container for the session and yield its admin connection string.

    Ryuk — testcontainers' cleanup sidecar — is disabled by default because it
    bind-mounts the Docker socket, which Docker Desktop on macOS refuses. The
    container is stopped by the context manager either way.

    Yields:
        The container's superuser connection string.
    """
    if os.environ.get("MARKETING_OS_TEST_POSTGRES") != "1":
        pytest.skip("Postgres suite is opt-in: set MARKETING_OS_TEST_POSTGRES=1 (needs Docker).")
    os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")
    from testcontainers.community.postgres import PostgresContainer

    with PostgresContainer(POSTGRES_IMAGE) as container:
        yield container.get_connection_url(driver=None)


@pytest.fixture(scope="session")
def postgres_dsn(postgres_superuser_dsn: str) -> str:
    """Create the schema and the application role, and yield the app's connection string.

    The suite connects as an ordinary role on purpose: row-level security does
    not constrain a superuser, so connecting as one would assert tenant
    isolation that production does not have. The password is a throwaway
    credential for a container that lives for one test session.

    Args:
        postgres_superuser_dsn: The container's admin connection string.

    Returns:
        The connection string the adapters use, as the non-superuser app role.
    """
    import psycopg

    from marketing_os.adapters.postgres.schema import ensure_schema, grant_application_role_sql

    with psycopg.connect(postgres_superuser_dsn, autocommit=True) as connection:
        ensure_schema(connection)
        connection.execute(_CREATE_APP_ROLE)
        connection.execute(grant_application_role_sql(APP_ROLE))
    return _with_credentials(postgres_superuser_dsn, APP_ROLE, APP_PASSWORD)


@pytest.fixture
def postgres_pool(postgres_dsn: str, postgres_superuser_dsn: str) -> Iterator[Any]:
    """Yield a fresh connection pool over empty tables.

    Every harness table is truncated, derived from the schema's own table list
    rather than spelled out here — a table added to the schema and forgotten in a
    hand-written list leaks rows between tests, which shows up as a failure in
    whichever test happens to run second.

    Args:
        postgres_dsn: The application role's connection string.
        postgres_superuser_dsn: The admin connection string, used to truncate.

    Yields:
        An open ``psycopg_pool.ConnectionPool`` for the application role.
    """
    import psycopg
    from psycopg_pool import ConnectionPool

    from marketing_os.adapters.postgres.schema import TABLES

    with psycopg.connect(postgres_superuser_dsn, autocommit=True) as connection:
        connection.execute(f"TRUNCATE {', '.join(TABLES)}")
    with ConnectionPool(postgres_dsn, open=True) as pool:
        yield pool

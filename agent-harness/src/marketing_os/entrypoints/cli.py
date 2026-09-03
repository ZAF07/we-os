"""Command-line interface for the Marketing OS graph.

Commands::

    marketing-os new-campaign <slug> [--stage K] [--provider P]
    marketing-os check <slug>
    marketing-os agents
    marketing-os init-db --dsn <admin dsn> [--app-role NAME]
    marketing-os publish-questionnaire --dsn <dsn> --file <question set json>

Mirrors ``/new-campaign``: the Stage 0 gate runs first, then the pipeline.
Progress is streamed from the graph's custom events.

The CLI is a **local operator tool**, so there is no request and no token to
verify. Its tenant therefore comes from configuration (``MARKETING_OS_TENANT_ID``)
rather than a command-line argument — a business identity typed by the caller is
exactly what ADR-0013 forbids, whichever entrypoint accepts it.

The Stage 0 gate it applies is the same one the API applies: the published
question set defines the Required Brand DNA fields (ADR-0018), so the two
entrypoints cannot disagree about whether a business may run. See
:func:`resolve_questionnaire`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from marketing_os.adapters.documents import FilesystemDocumentStore
from marketing_os.adapters.observability import configure_logging, configure_tracing
from marketing_os.config import Settings, load_settings
from marketing_os.entrypoints.env import load_env
from marketing_os.errors import ConfigError, GateError, GuardrailError, MarketingOSError
from marketing_os.governance import check_gate
from marketing_os.governance.gate import GateReport
from marketing_os.questionnaire import SEED_QUESTIONNAIRE
from marketing_os.schemas import Questionnaire


def _resolve_tenant(settings: Settings) -> str:
    """Return the tenant the CLI operates as.

    Args:
        settings: The harness settings.

    Returns:
        The configured tenant id.

    Raises:
        ConfigError: If no tenant is configured, rather than defaulting to one
            and writing a business's documents into the wrong place.
    """
    if not settings.tenant_id:
        raise ConfigError(
            "No tenant configured. Set MARKETING_OS_TENANT_ID to the tenant this "
            "CLI operates as (the organization id from your IdP)."
        )
    return settings.tenant_id


CONNECT_TIMEOUT_SECONDS = 5.0


def read_published_questionnaire(dsn: str) -> Questionnaire:
    """Return the question set published to a database, closing the pool after.

    The connect timeout is short because this runs before an operator's command
    does anything: a database that is not listening should say so promptly
    rather than after the pool's much longer default.

    Args:
        dsn: The Postgres connection string.

    Returns:
        The published question set.
    """
    from psycopg_pool import ConnectionPool

    from marketing_os.adapters.postgres import PostgresQuestionnaireStore

    with ConnectionPool(dsn, open=True, timeout=CONNECT_TIMEOUT_SECONDS) as pool:
        return PostgresQuestionnaireStore(pool).published()


def resolve_questionnaire(settings: Settings) -> tuple[Questionnaire, str]:
    """Return the question set the gate enforces, and where it came from.

    The API gates against the published question set (ADR-0018), so the CLI must
    too, or publishing a question set with a new Required question tightens the
    gate for one entrypoint and not the other — and ``new-campaign`` would run
    the pipeline for a business whose Brand DNA the API refuses.

    With no database configured there is nothing published to read, so the
    code-shipped seed set applies — the same set the service serves against an
    empty ``questionnaires`` table. The source is returned so a passing gate can
    say which set it enforced rather than printing a bare green checkmark.

    Args:
        settings: The harness settings carrying the optional Postgres DSN.

    Returns:
        The question set, and a short description of where it was resolved from.

    Raises:
        ConfigError: If a DSN is configured but the database cannot be read.
            Falling back to the seed set there would let the CLI pass a business
            the API blocks, which is the disagreement this gate exists to close.
    """
    if not settings.postgres_dsn:
        return SEED_QUESTIONNAIRE, "the built-in seed set, no database configured"
    try:
        published = read_published_questionnaire(settings.postgres_dsn)
    except Exception as exc:
        raise ConfigError(
            "Could not read the published question set from the database named by "
            f"MARKETING_OS_POSTGRES_DSN: {exc}. Start the database, or unset the "
            "variable to gate against the built-in seed set."
        ) from exc
    return published, "the set published to the database"


def _print_gate(report: GateReport, questionnaire: Questionnaire, source: str) -> bool:
    """Print a gate report and return whether it passed.

    Args:
        report: The Stage 0 gate report.
        questionnaire: The question set the gate enforced.
        source: Where that question set was resolved from.

    Returns:
        ``True`` when the gate passed, ``False`` otherwise.
    """
    if report.ok:
        print(f"✓ Stage 0 gate passed for tenant '{report.tenant}', campaign '{report.slug}'.")
        print(
            f"    Gated against question set v{questionnaire.version} "
            f"({len(questionnaire.required_questions)} Required fields) — {source}."
        )
        return True
    print(f"✗ Stage 0 gate FAILED for tenant '{report.tenant}', campaign '{report.slug}':")
    for issue in report.all_issues:
        print(f"    - {issue}")
    return False


def _render_event(event: dict[str, Any]) -> None:
    """Render one streamed progress event to stdout.

    Args:
        event: The event dictionary emitted by a graph node.
    """
    name = event.get("event")
    if name == "stage.start":
        print(f"\n── Stage: {event['stage']} (agent: {event['agent']}) " + "─" * 20)
    elif name == "stage.review":
        count = len(event.get("discrepancies", []))
        status = "PASS" if event["passed"] else f"{count} issue(s): {event.get('summary', '')}"
        print(f"  [QA iter {event['iteration']}] {status}")
    elif name == "stage.save_retry":
        print(f"  [save retry {event['attempt']}] asking agent to write its deliverable")
    elif name == "stage.done":
        print(f"  ✓ wrote {event['deliverable']} (QA iterations: {event['qa_iterations']})")
    elif name == "stage.failed":
        print(f"  ✗ stage failed ({event.get('reason', '?')}): {event.get('summary', '')}")
    elif name == "stage.blocked":
        print(f"  ✗ blocked: prerequisite '{event['prerequisite']}' missing")


def _cmd_check(args: argparse.Namespace) -> int:
    """Run only the Stage 0 gate.

    Args:
        args: Parsed CLI arguments.

    Returns:
        The process exit code (0 on pass, 1 on fail).
    """
    settings = load_settings()
    tenant = _resolve_tenant(settings)
    questionnaire, source = resolve_questionnaire(settings)
    report = check_gate(
        settings,
        tenant,
        args.slug,
        store=FilesystemDocumentStore(settings.root),
        questionnaire=questionnaire,
    )
    return 0 if _print_gate(report, questionnaire, source) else 1


def _cmd_agents(args: argparse.Namespace) -> int:
    """List the specialist agents and the tools they are granted.

    Args:
        args: Parsed CLI arguments.

    Returns:
        The process exit code.
    """
    from marketing_os.agents import load_all_agents

    settings = load_settings()
    for name, spec in load_all_agents(settings).items():
        print(f"{name:24} tools=[{', '.join(spec.tools)}]")
    return 0


def _cmd_new_campaign(args: argparse.Namespace) -> int:
    """Run the pipeline (or a single stage) for the configured tenant.

    A run that reaches a stage requiring human approval stops there and says so
    (ADR-0015). Approving is an API operation — the CLI is a local operator tool
    with no gate to answer at — so it reports the halt rather than claiming the
    campaign is complete.

    Args:
        args: Parsed CLI arguments.

    Returns:
        The process exit code.
    """
    settings = load_settings()
    if args.provider:
        settings.provider = args.provider
    tenant = _resolve_tenant(settings)
    slug = args.slug

    questionnaire, source = resolve_questionnaire(settings)
    report = check_gate(
        settings,
        tenant,
        slug,
        store=FilesystemDocumentStore(settings.root),
        questionnaire=questionnaire,
    )
    if not _print_gate(report, questionnaire, source):
        return 1

    from marketing_os.graph.runner import run_campaign

    result = run_campaign(settings, tenant, slug, stage=args.stage, on_event=_render_event)
    print("\n" + "=" * 60)
    if result.awaiting_approval_stage:
        print(
            f"Campaign '{result.slug}' is waiting for your approval of "
            f"'{result.awaiting_approval_stage}'. Stages run: {len(result.stages)}"
        )
    else:
        print(f"Campaign '{result.slug}' complete. Stages run: {len(result.stages)}")
    for stage_result in result.stages:
        print(
            f"  - {stage_result.stage}: {stage_result.deliverable_path}  "
            f"(QA iters {stage_result.qa_iterations})"
        )
    print(f"Tokens — in: {result.usage.input_tokens}, out: {result.usage.output_tokens}")
    if result.run_log:
        print(f"Run log: {result.run_log}")
    return 0


def _cmd_init_db(args: argparse.Namespace) -> int:
    """Provision a Postgres database for the harness.

    This is the one command that needs administrative rights, and it is separate
    from serving on purpose: the service connects as an ordinary role with no
    power to create or alter tables, because row-level security is not much of a
    boundary if the application can drop the policy enforcing it.

    Args:
        args: Parsed CLI arguments carrying the administrative DSN and the
            optional application role to grant.

    Returns:
        The process exit code.
    """
    import psycopg
    from langgraph.checkpoint.postgres import PostgresSaver

    from marketing_os.adapters.postgres.schema import (
        ensure_schema,
        grant_application_role_sql,
        schema_drift,
    )

    with psycopg.connect(args.dsn, autocommit=True) as connection:
        ensure_schema(connection)
        remaining = schema_drift(connection)
        if remaining:
            print("✗ The database is still out of date after provisioning. Missing:")
            for item in remaining:
                print(f"    - {item}")
            print(
                "These cannot be added in place. Migrate the database, or recreate it "
                "(`make db-down` destroys its data)."
            )
            return 1
        print("The tenants, documents and runs tables, indexes and RLS policy are up to date.")

    with PostgresSaver.from_conn_string(args.dsn) as saver:
        saver.setup()
    print("The LangGraph checkpointer tables are up to date.")

    if args.app_role:
        with psycopg.connect(args.dsn, autocommit=True) as connection:
            connection.execute(grant_application_role_sql(args.app_role))
        print(f"'{args.app_role}' has table access.")
        print(
            f"Point MARKETING_OS_POSTGRES_DSN at this database as '{args.app_role}' — "
            "never as a superuser, which bypasses row-level security."
        )
    return 0


def load_questionnaire_file(path: Path) -> Questionnaire:
    """Read and validate an admin-authored question set from a JSON file.

    Validating here rather than at the database means a malformed set — a
    question missing its ``why_we_ask``, an unknown field — is refused before it
    can reach a single business's onboarding.

    Args:
        path: The JSON file holding the question set.

    Returns:
        The parsed question set.

    Raises:
        ConfigError: If the file is absent or is not a valid question set.
    """
    if not path.is_file():
        raise ConfigError(f"No question set at {path}.")
    try:
        return Questionnaire.model_validate_json(path.read_text(encoding="utf-8"))
    except ValidationError as exc:
        raise ConfigError(f"{path} is not a valid question set: {exc}") from exc


def _cmd_publish_questionnaire(args: argparse.Namespace) -> int:
    """Publish a new version of the admin-curated question set.

    This is the path that makes "editable without a deploy" true: the admin
    edits the question set as JSON and publishes it, which changes the
    onboarding wizard and what the DNA Gate enforces as Required together, since
    both read the published version (ADR-0018).

    Args:
        args: Parsed CLI arguments carrying the DSN and the question-set file.

    Returns:
        The process exit code.
    """
    from psycopg_pool import ConnectionPool

    from marketing_os.adapters.postgres import PostgresQuestionnaireStore

    questionnaire = load_questionnaire_file(Path(args.file))
    with ConnectionPool(args.dsn, open=True) as pool:
        published = PostgresQuestionnaireStore(pool).publish(questionnaire)
    required = [question.field for question in published.required_questions]
    print(f"Published question set v{published.version}: {len(published.questions)} questions.")
    print(f"The DNA Gate now requires {len(required)} fields: {', '.join(required)}")
    print("Businesses whose answers predate this version are prompted to answer what is new.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser.

    Returns:
        The configured argument parser.
    """
    parser = argparse.ArgumentParser(prog="marketing-os", description="Marketing OS agent graph.")
    sub = parser.add_subparsers(dest="command", required=True)

    new_campaign = sub.add_parser("new-campaign", help="Run the pipeline for a campaign.")
    new_campaign.add_argument("slug", help="Campaign slug.")
    new_campaign.add_argument("--stage", help="Run only this stage (e.g. research).")
    new_campaign.add_argument("--provider", help="Override provider (deepseek|anthropic|openai).")
    new_campaign.set_defaults(func=_cmd_new_campaign)

    check = sub.add_parser("check", help="Run only the Stage 0 gate.")
    check.add_argument("slug", help="Campaign slug.")
    check.set_defaults(func=_cmd_check)

    agents = sub.add_parser("agents", help="List the specialist agents and their tools.")
    agents.set_defaults(func=_cmd_agents)

    init_db = sub.add_parser("init-db", help="Create the Postgres schema and grant the app role.")
    init_db.add_argument("--dsn", required=True, help="Administrative Postgres connection string.")
    init_db.add_argument("--app-role", help="Role the service connects as, to grant table access.")
    init_db.set_defaults(func=_cmd_init_db)

    publish = sub.add_parser(
        "publish-questionnaire", help="Publish a new version of the onboarding question set."
    )
    publish.add_argument("--dsn", required=True, help="Postgres connection string.")
    publish.add_argument("--file", required=True, help="JSON file holding the question set.")
    publish.set_defaults(func=_cmd_publish_questionnaire)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI.

    Args:
        argv: Optional argument vector; defaults to ``sys.argv``.

    Returns:
        The process exit code.
    """
    load_env()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        settings = load_settings()
        configure_logging(settings)
        configure_tracing(settings)
    except MarketingOSError as exc:
        print(f"\nConfig error: {exc}", file=sys.stderr)
        return 1
    try:
        exit_code: int = args.func(args)
        return exit_code
    except GateError as exc:
        print(f"\nGate error: {exc}", file=sys.stderr)
        return exc.exit_code
    except GuardrailError as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        for discrepancy in exc.discrepancies:
            print(
                f"  - [{discrepancy.get('rubric_point')}] {discrepancy.get('problem')}",
                file=sys.stderr,
            )
        if exc.run_log:
            print(f"Run log: {exc.run_log}", file=sys.stderr)
        return exc.exit_code
    except MarketingOSError as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        if exc.run_log:
            print(f"Run log: {exc.run_log}", file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    raise SystemExit(main())

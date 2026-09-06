"""Administrative command-line interface for Marketing OS.

Commands::

    marketing-os init-db --dsn <admin dsn> [--app-role NAME]
    marketing-os publish-questionnaire --dsn <dsn> --file <question set json>

Neither command runs a campaign. A campaign runs one way — ``POST
/campaigns/{slug}/runs`` on the API, driven by the frontend — so there is a
single execution surface that charges usage, versions deliverables and gates
against the published question set (ADR-0026).

What remains here has no API equivalent and needs rights the service
deliberately lacks: ``init-db`` provisions the schema and grants the application
role (ADR-0023), and ``publish-questionnaire`` is the path that makes the
onboarding question set editable without a deploy (ADR-0018). Both are invoked
by the compose ``migrate`` service.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pydantic import ValidationError

from marketing_os.adapters.observability import configure_logging, configure_tracing
from marketing_os.config import load_settings
from marketing_os.entrypoints.env import load_env
from marketing_os.errors import ConfigError, MarketingOSError
from marketing_os.schemas import Questionnaire


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
    parser = argparse.ArgumentParser(
        prog="marketing-os", description="Marketing OS administrative commands."
    )
    sub = parser.add_subparsers(dest="command", required=True)

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
    except MarketingOSError as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        if exc.run_log:
            print(f"Run log: {exc.run_log}", file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    raise SystemExit(main())

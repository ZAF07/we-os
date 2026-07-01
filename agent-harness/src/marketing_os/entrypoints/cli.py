"""Command-line interface for the Marketing OS graph.

Commands::

    marketing-os new-campaign <name> [--slug S] [--stage K] [--provider P]
    marketing-os check <name> [--slug S]
    marketing-os agents

Mirrors ``/new-campaign <name>``: the Stage 0 gate runs first, then the pipeline.
Progress is streamed from the graph's custom events.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from marketing_os.adapters.observability import configure_logging, configure_tracing
from marketing_os.config import load_settings
from marketing_os.errors import GateError, MarketingOSError
from marketing_os.governance import check_gate
from marketing_os.governance.gate import GateReport


def _print_gate(report: GateReport) -> bool:
    """Print a gate report and return whether it passed.

    Args:
        report: The Stage 0 gate report.

    Returns:
        ``True`` when the gate passed, ``False`` otherwise.
    """
    if report.ok:
        print(f"✓ Stage 0 gate passed for customer '{report.customer}', campaign '{report.slug}'.")
        return True
    print(f"✗ Stage 0 gate FAILED for customer '{report.customer}', campaign '{report.slug}':")
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
    slug = args.slug or args.name
    report = check_gate(settings, args.name, slug)
    return 0 if _print_gate(report) else 1


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
    """Run the pipeline (or a single stage) for a customer.

    Args:
        args: Parsed CLI arguments.

    Returns:
        The process exit code.
    """
    settings = load_settings()
    if args.provider:
        settings.provider = args.provider
    slug = args.slug or args.name

    report = check_gate(settings, args.name, slug)
    if not _print_gate(report):
        return 1

    from marketing_os.graph.runner import run_campaign

    result = run_campaign(settings, args.name, slug, stage=args.stage, on_event=_render_event)
    print("\n" + "=" * 60)
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


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser.

    Returns:
        The configured argument parser.
    """
    parser = argparse.ArgumentParser(prog="marketing-os", description="Marketing OS agent graph.")
    sub = parser.add_subparsers(dest="command", required=True)

    new_campaign = sub.add_parser("new-campaign", help="Run the pipeline for a customer.")
    new_campaign.add_argument("name", help="Customer name (folder under customers/).")
    new_campaign.add_argument("--slug", help="Campaign slug (default: same as customer name).")
    new_campaign.add_argument("--stage", help="Run only this stage (e.g. research).")
    new_campaign.add_argument("--provider", help="Override provider (deepseek|anthropic|openai).")
    new_campaign.set_defaults(func=_cmd_new_campaign)

    check = sub.add_parser("check", help="Run only the Stage 0 gate.")
    check.add_argument("name")
    check.add_argument("--slug")
    check.set_defaults(func=_cmd_check)

    agents = sub.add_parser("agents", help="List the specialist agents and their tools.")
    agents.set_defaults(func=_cmd_agents)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI.

    Args:
        argv: Optional argument vector; defaults to ``sys.argv``.

    Returns:
        The process exit code.
    """
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
        return 1
    except MarketingOSError as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        for discrepancy in getattr(exc, "detail", {}).get("discrepancies", []):
            print(
                f"  - [{discrepancy.get('rubric_point')}] {discrepancy.get('problem')}",
                file=sys.stderr,
            )
        run_log = getattr(exc, "run_log", None)
        if run_log:
            print(f"Run log: {run_log}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

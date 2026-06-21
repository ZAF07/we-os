"""Command-line interface.

  marketing-os new-campaign <name> [--slug S] [--stage K] [--provider P] [--no-stream]
  marketing-os check <name> [--slug S]
  marketing-os agents

Mirrors `/new-campaign <name>`: gate first, then the pipeline.
"""

from __future__ import annotations

import argparse
import sys

from .config import load_settings
from .errors import GateError, MarketingOSError
from .governance import check_gate


def _print_gate(report) -> bool:
    if report.ok:
        print(f"✓ Stage 0 gate passed for customer '{report.customer}', campaign '{report.slug}'.")
        return True
    print(f"✗ Stage 0 gate FAILED for customer '{report.customer}', campaign '{report.slug}':")
    for issue in report.all_issues:
        print(f"    - {issue}")
    return False


def _cmd_check(args) -> int:
    settings = load_settings()
    slug = args.slug or args.name
    report = check_gate(settings, args.name, slug)
    return 0 if _print_gate(report) else 1


def _cmd_agents(args) -> int:
    from .agents import load_all_agents

    settings = load_settings()
    for name, spec in load_all_agents(settings).items():
        print(f"{name:24} tools=[{', '.join(spec.tools)}]")
    return 0


def _cmd_new_campaign(args) -> int:
    settings = load_settings()
    if args.provider:
        settings.provider = args.provider
    if args.no_stream:
        settings.stream = False
    slug = args.slug or args.name

    # Gate up front with a clear message, matching the orchestrator's stop behavior.
    report = check_gate(settings, args.name, slug)
    if not _print_gate(report):
        return 1

    from .loop import StreamToStdout
    from .orchestrator import MarketingDirector

    def on_event(e: dict) -> None:
        ev = e.get("event")
        if ev == "stage.start":
            print(f"\n── Stage: {e['stage']} (agent: {e['agent']}) " + "─" * 20)
        elif ev == "stage.review":
            status = "PASS" if e["passed"] else f"{e['discrepancies']} issue(s)"
            print(f"\n  [QA iter {e['iteration']}] {status}")
        elif ev == "stage.save_retry":
            print(f"\n  [save retry {e['attempt']}] asking agent to write its deliverable")
        elif ev == "stage.done":
            print(f"\n  ✓ wrote {e['deliverable']} (QA iterations: {e['qa_iterations']})")

    director = MarketingDirector(
        settings,
        hooks=StreamToStdout() if settings.stream else None,
        on_event=on_event,
    )
    result = director.run_campaign(args.name, slug, only_stage=args.stage)

    print("\n" + "=" * 60)
    print(f"Campaign '{result.slug}' complete. Stages run: {len(result.stages)}")
    for s in result.stages:
        print(f"  - {s.stage}: {s.deliverable_path}  (QA iters {s.qa_iterations})")
    u = result.usage
    print(f"Tokens — in: {u.input_tokens}, out: {u.output_tokens}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="marketing-os", description="Marketing OS agent harness.")
    sub = p.add_subparsers(dest="command", required=True)

    nc = sub.add_parser("new-campaign", help="Run the pipeline for a customer.")
    nc.add_argument("name", help="Customer name (folder under customers/).")
    nc.add_argument("--slug", help="Campaign slug (default: same as customer name).")
    nc.add_argument("--stage", help="Run only this stage (e.g. research).")
    nc.add_argument("--provider", help="Override provider (deepseek|anthropic|openai).")
    nc.add_argument("--no-stream", action="store_true", help="Disable token streaming.")
    nc.set_defaults(func=_cmd_new_campaign)

    ck = sub.add_parser("check", help="Run only the Stage 0 gate.")
    ck.add_argument("name")
    ck.add_argument("--slug")
    ck.set_defaults(func=_cmd_check)

    ag = sub.add_parser("agents", help="List the specialist agents and their tools.")
    ag.set_defaults(func=_cmd_agents)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except GateError as exc:
        print(f"\nGate error: {exc}", file=sys.stderr)
        return 1
    except MarketingOSError as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

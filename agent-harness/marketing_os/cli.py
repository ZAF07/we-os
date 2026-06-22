"""Command-line interface.

    marketing-os new-campaign <customer> [--slug S] [--provider P] [--show]
    marketing-os check <customer> [--slug S]
    marketing-os agents

`new-campaign` runs the Stage-0 gate, then the full coordinator pipeline, printing
progress. If any agent requests human approval, the CLI prompts inline (blocking)
and resumes the run with the decision.
"""

from __future__ import annotations

import argparse
import sys

from .config import load_settings
from .errors import MarketingOSError
from .governance import check_gate


def _print_gate(report) -> bool:
    """Print a gate report; return True if it passed."""
    if report.ok:
        print(f"✓ Stage 0 gate passed (customer '{report.customer}', campaign '{report.slug}').")
        return True
    print(f"✗ Stage 0 gate FAILED (customer '{report.customer}', campaign '{report.slug}'):")
    for issue in report.all_issues:
        print(f"    - {issue}")
    return False


def _cli_approval_handler(payload: dict) -> dict:
    """Blocking terminal prompt used to resolve a human-approval request."""
    print("\n" + "=" * 60)
    print("HUMAN APPROVAL REQUESTED")
    print(f"  summary: {payload.get('summary', '')}")
    if payload.get("details"):
        print(f"  details: {payload['details']}")
    print(f"  risk:    {payload.get('risk_level', 'medium')}")
    answer = input("Approve? [y/N] ").strip().lower()
    if answer == "y":
        return {"status": "approved"}
    comment = input("Rejection reason (optional): ").strip()
    return {"status": "rejected", "comment": comment}


def _on_event(e: dict) -> None:
    """Compact progress printer for the CLI."""
    ev = e.get("event")
    if ev == "gate.passed":
        print("Gate passed; starting pipeline.\n")
    elif ev == "resume":
        done = ", ".join(e.get("completed", [])) or "(nothing yet)"
        print(f"Resuming — already complete: {done}. Skipping those stages.\n")
    elif ev == "transient_retry":
        print(f"\n⏳ transient error (attempt {e.get('attempt')}); retrying in "
              f"{e.get('delay_s')}s and resuming where it stopped…")
    elif ev == "step" and e.get("envelope"):
        env = e["envelope"]
        flag = "  ⚠" if e.get("violations") else ""
        print(f"[{e.get('stage')}] {env.get('next_action','?')} — {env.get('thought_summary','')[:80]}{flag}")
    elif ev == "step" and e.get("violations"):
        print(f"[{e.get('stage')}] guardrail flags: {e['violations']}")
    elif ev == "approval.resolved":
        print(f"  approval -> {e.get('status')}")
    elif ev == "campaign.done":
        print(f"\nDone. Deliverables: {', '.join(e.get('stages', []))}")


def _cmd_check(args) -> int:
    settings = load_settings()
    report = check_gate(settings, args.name, args.slug or args.name)
    return 0 if _print_gate(report) else 1


def _cmd_agents(args) -> int:
    from .agents import load_registry

    reg = load_registry(load_settings())
    for key, cfg in reg.agents.items():
        hc = " human_check" if cfg.human_check else ""
        print(f"{key:14} tools={cfg.tools}{hc}")
    print(f"approval gate enabled: {reg.approval_enabled}")
    return 0


def _cmd_new_campaign(args) -> int:
    settings = load_settings()
    slug = args.slug or args.name
    report = check_gate(settings, args.name, slug)
    if not _print_gate(report):
        return 1

    from .orchestrator import MarketingDirector

    director = MarketingDirector(
        settings,
        provider=args.provider,
        on_event=_on_event,
        approval_handler=_cli_approval_handler,
        headless=not args.show,
    )
    result = director.run_campaign_sync(args.name, slug, fresh=args.fresh)
    print("\n" + "=" * 60)
    print(f"Campaign '{result.slug}' complete.")
    print(f"  stages produced : {', '.join(result.deliverables) or '(none)'}")
    print(f"  steps captured  : {len(result.steps)}")
    if result.violations:
        print(f"  guardrail flags : {len(result.violations)}")
    print(f"  deliverable files under: campaigns/{slug}/")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse CLI."""
    p = argparse.ArgumentParser(prog="marketing-os", description="ADK marketing agent harness.")
    sub = p.add_subparsers(dest="command", required=True)

    nc = sub.add_parser("new-campaign", help="Run the pipeline for a customer.")
    nc.add_argument("name", help="Customer folder name under customers/.")
    nc.add_argument("--slug", help="Campaign slug (default: customer name).")
    nc.add_argument("--provider", help="Override provider (gemini|deepseek|anthropic|openai).")
    nc.add_argument("--show", action="store_true", help="Run the browser non-headless.")
    nc.add_argument(
        "--fresh",
        action="store_true",
        help="Ignore any saved checkpoint and start over (default: resume where it stopped).",
    )
    nc.set_defaults(func=_cmd_new_campaign)

    ck = sub.add_parser("check", help="Run only the Stage 0 gate.")
    ck.add_argument("name")
    ck.add_argument("--slug")
    ck.set_defaults(func=_cmd_check)

    ag = sub.add_parser("agents", help="List agents and their tool grants.")
    ag.set_defaults(func=_cmd_agents)
    return p


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except MarketingOSError as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

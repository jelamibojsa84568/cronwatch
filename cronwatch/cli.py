"""CLI entry-point for cronwatch."""

from __future__ import annotations

import argparse
import sys

from cronwatch.config import load_config
from cronwatch.history import get_history, last_failed
from cronwatch.report import build_report, format_report_text
from cronwatch.runner import run_job
from cronwatch.scheduler import get_due_jobs, parse_jobs
from cronwatch.watcher import execute_and_watch


# ---------------------------------------------------------------------------
# Sub-command handlers
# ---------------------------------------------------------------------------

def cmd_run(args: argparse.Namespace, config: dict) -> int:
    """Run a single named job immediately."""
    jobs = parse_jobs(config)
    matches = [j for j in jobs if j["name"] == args.job]
    if not matches:
        print(f"[cronwatch] Job {args.job!r} not found in config.", file=sys.stderr)
        return 1
    result = execute_and_watch(matches[0], config)
    print(result)
    return 0 if result.success else 2


def cmd_check_due(args: argparse.Namespace, config: dict) -> int:
    """Print jobs that are currently due to run."""
    jobs = parse_jobs(config)
    due = get_due_jobs(jobs, config.get("history_dir", "/var/log/cronwatch"))
    if not due:
        print("[cronwatch] No jobs are currently due.")
    for job in due:
        print(f"  DUE  {job['name']}  ({job['schedule']})")
    return 0


def cmd_history(args: argparse.Namespace, config: dict) -> int:
    """Show run history for a job."""
    history_dir = config.get("history_dir", "/var/log/cronwatch")
    entries = get_history(args.job, history_dir, limit=args.limit)
    if not entries:
        print(f"[cronwatch] No history found for {args.job!r}.")
        return 0
    for e in entries:
        status = "OK" if e.get("success") else "FAIL"
        print(f"  {e['timestamp']}  [{status}]  exit={e.get('exit_code')}  duration={e.get('duration_s')}s")
    return 0


def cmd_last_failed(args: argparse.Namespace, config: dict) -> int:
    """Show the last failure for a job."""
    history_dir = config.get("history_dir", "/var/log/cronwatch")
    entry = last_failed(args.job, history_dir)
    if not entry:
        print(f"[cronwatch] No failures recorded for {args.job!r}.")
        return 0
    print(f"Last failure: {entry['timestamp']}  exit={entry.get('exit_code')}")
    if entry.get("stderr"):
        print("stderr:", entry["stderr"])
    return 0


def cmd_report(args: argparse.Namespace, config: dict) -> int:
    """Print a summary report for all configured jobs."""
    jobs = parse_jobs(config)
    history_dir = config.get("history_dir", "/var/log/cronwatch")
    report = build_report(jobs, history_dir, window=args.window)
    print(format_report_text(report))
    return 0


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwatch",
        description="Monitor, log, and alert on cron job failures.",
    )
    parser.add_argument("--config", default=None, help="Path to config file.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Run a job by name.")
    p_run.add_argument("job", help="Job name.")

    sub.add_parser("check-due", help="List jobs that are due to run.")

    p_hist = sub.add_parser("history", help="Show run history for a job.")
    p_hist.add_argument("job", help="Job name.")
    p_hist.add_argument("--limit", type=int, default=20)

    p_lf = sub.add_parser("last-failed", help="Show last failure for a job.")
    p_lf.add_argument("job", help="Job name.")

    p_report = sub.add_parser("report", help="Print a summary report.")
    p_report.add_argument("--window", default="24h", help="Time window e.g. 24h, 7d.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config(args.config)

    handlers = {
        "run": cmd_run,
        "check-due": cmd_check_due,
        "history": cmd_history,
        "last-failed": cmd_last_failed,
        "report": cmd_report,
    }
    return handlers[args.command](args, config)


if __name__ == "__main__":
    sys.exit(main())

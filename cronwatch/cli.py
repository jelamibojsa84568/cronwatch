"""CLI entry point for cronwatch."""

import argparse
import sys
from typing import Optional

from cronwatch.config import load_config
from cronwatch.history import get_history, last_failed
from cronwatch.runner import run_job
from cronwatch.scheduler import parse_jobs, get_due_jobs


def cmd_run(args: argparse.Namespace) -> int:
    """Run a named job immediately and log the result."""
    config = load_config(args.config)
    jobs = parse_jobs(config)
    target = next((j for j in jobs if j["name"] == args.job_name), None)
    if target is None:
        print(f"Error: job '{args.job_name}' not found in config.", file=sys.stderr)
        return 1
    result = run_job(target)
    status = "SUCCESS" if result.success else "FAILED"
    print(f"[{status}] {result.job_name} exited with code {result.exit_code}")
    if not result.success and result.stderr:
        print(f"stderr: {result.stderr}")
    return 0 if result.success else 1


def cmd_check_due(args: argparse.Namespace) -> int:
    """Print jobs that are currently due to run."""
    config = load_config(args.config)
    jobs = parse_jobs(config)
    due = get_due_jobs(jobs)
    if not due:
        print("No jobs are currently due.")
        return 0
    for job in due:
        print(f"  - {job['name']} ({job['schedule']})")
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    """Display recent execution history, optionally filtered by job name."""
    config = load_config(args.config)
    history_file = config.get("history_file", "/var/log/cronwatch/history.json")
    entries = get_history(
        job_name=args.job_name or None,
        limit=args.limit,
        history_file=history_file,
    )
    if not entries:
        print("No history found.")
        return 0
    for entry in entries:
        status = "OK" if entry.get("success") else "FAIL"
        print(
            f"[{entry['timestamp']}] [{status}] {entry['job_name']} "
            f"exit={entry['exit_code']} duration={entry.get('duration', '?'):.2f}s"
        )
    return 0


def cmd_last_failed(args: argparse.Namespace) -> int:
    """Show the most recent failure for a specific job."""
    config = load_config(args.config)
    history_file = config.get("history_file", "/var/log/cronwatch/history.json")
    entry = last_failed(args.job_name, history_file=history_file)
    if entry is None:
        print(f"No failures recorded for '{args.job_name}'.")
        return 0
    print(f"Last failure for '{args.job_name}':")
    print(f"  Timestamp : {entry['timestamp']}")
    print(f"  Exit code : {entry['exit_code']}")
    print(f"  Duration  : {entry.get('duration', '?'):.2f}s")
    if entry.get("stderr"):
        print(f"  stderr    : {entry['stderr']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwatch", description="Monitor and log cron job executions."
    )
    parser.add_argument("--config", default=None, help="Path to config file.")
    sub = parser.add_subparsers(dest="command")

    p_run = sub.add_parser("run", help="Run a job by name.")
    p_run.add_argument("job_name", help="Name of the job to run.")

    sub.add_parser("check-due", help="List jobs that are currently due.")

    p_hist = sub.add_parser("history", help="Show execution history.")
    p_hist.add_argument("job_name", nargs="?", default=None, help="Filter by job name.")
    p_hist.add_argument("--limit", type=int, default=20, help="Max entries to show.")

    p_lf = sub.add_parser("last-failed", help="Show last failure for a job.")
    p_lf.add_argument("job_name", help="Name of the job.")

    return parser


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    dispatch = {
        "run": cmd_run,
        "check-due": cmd_check_due,
        "history": cmd_history,
        "last-failed": cmd_last_failed,
    }
    if args.command not in dispatch:
        parser.print_help()
        return 1
    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main())

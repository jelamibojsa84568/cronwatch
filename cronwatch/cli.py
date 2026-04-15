"""Command-line entry point for cronwatch.

Usage:
    cronwatch run [--config PATH] [--dry-run]
    cronwatch check-due [--config PATH]
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime

from cronwatch.config import load_config
from cronwatch.logger import log_job_result, setup_job_logger
from cronwatch.notifier import build_failure_email, send_email_alert
from cronwatch.runner import run_job
from cronwatch.scheduler import get_due_jobs, parse_jobs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("cronwatch")


def cmd_run(args: argparse.Namespace) -> int:
    """Run all jobs that are currently due."""
    config = load_config(args.config)
    jobs = parse_jobs(config)
    due = get_due_jobs(jobs, reference_time=datetime.utcnow())

    if not due:
        logger.info("No jobs are due at this time.")
        return 0

    exit_codes = []
    for job in due:
        if args.dry_run:
            logger.info("[dry-run] Would execute job '%s': %s", job["name"], job["command"])
            continue

        job_logger = setup_job_logger(job["name"], config.get("log_dir", "/var/log/cronwatch"))
        result = run_job(job["name"], job["command"], timeout=job.get("timeout"))
        log_job_result(job_logger, result)

        if not result.success:
            logger.warning("Job '%s' failed with exit code %d.", job["name"], result.exit_code)
            email_cfg = config.get("email")
            if email_cfg and email_cfg.get("enabled", False):
                msg = build_failure_email(result, email_cfg)
                send_email_alert(msg, email_cfg)

        exit_codes.append(result.exit_code)

    return 1 if any(c != 0 for c in exit_codes) else 0


def cmd_check_due(args: argparse.Namespace) -> int:
    """List jobs that are due right now without running them."""
    config = load_config(args.config)
    jobs = parse_jobs(config)
    due = get_due_jobs(jobs, reference_time=datetime.utcnow())

    if not due:
        print("No jobs are due.")
        return 0

    for job in due:
        print(f"  - {job['name']}  ({job['schedule']})  {job['command']}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwatch",
        description="Monitor, log, and alert on cron job failures.",
    )
    parser.add_argument("--config", default=None, metavar="PATH", help="Path to config file.")

    sub = parser.add_subparsers(dest="command")

    run_p = sub.add_parser("run", help="Execute all due jobs.")
    run_p.add_argument("--dry-run", action="store_true", help="Print jobs without running them.")
    run_p.set_defaults(func=cmd_run)

    check_p = sub.add_parser("check-due", help="List jobs due right now.")
    check_p.set_defaults(func=cmd_check_due)

    return parser


def main() -> None:  # pragma: no cover
    parser = build_parser()
    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(0)
    sys.exit(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    main()

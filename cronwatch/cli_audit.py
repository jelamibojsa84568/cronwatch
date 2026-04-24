"""CLI sub-commands for the audit log feature."""

from __future__ import annotations

import sys

import click

from cronwatch.audit import format_audit_text, read_audit_log
from cronwatch.config import load_config


@click.group("audit")
def audit() -> None:
    """Inspect the structured audit trail for cron jobs."""


@audit.command("show")
@click.argument("job_name")
@click.option("--config", "config_path", default=None, help="Path to config file.")
@click.option("--tail", default=0, help="Show only the last N events (0 = all).")
def cmd_show_audit(job_name: str, config_path: str | None, tail: int) -> None:
    """Print the audit log for JOB_NAME."""
    cfg = load_config(config_path)
    log_dir = cfg.get("log_dir", "/var/log/cronwatch")
    events = read_audit_log(log_dir, job_name)
    if tail > 0:
        events = events[-tail:]
    click.echo(format_audit_text(events))


@audit.command("count")
@click.argument("job_name")
@click.option("--config", "config_path", default=None, help="Path to config file.")
@click.option(
    "--failures-only",
    is_flag=True,
    default=False,
    help="Count only failed events.",
)
def cmd_audit_count(
    job_name: str, config_path: str | None, failures_only: bool
) -> None:
    """Print the number of audit events for JOB_NAME."""
    cfg = load_config(config_path)
    log_dir = cfg.get("log_dir", "/var/log/cronwatch")
    events = read_audit_log(log_dir, job_name)
    if failures_only:
        events = [e for e in events if not e.get("success", True)]
    click.echo(str(len(events)))


@audit.command("clear")
@click.argument("job_name")
@click.option("--config", "config_path", default=None, help="Path to config file.")
@click.confirmation_option(prompt="Delete audit log for this job?")
def cmd_clear_audit(job_name: str, config_path: str | None) -> None:
    """Delete the audit log file for JOB_NAME."""
    import os
    from cronwatch.audit import _audit_path

    cfg = load_config(config_path)
    log_dir = cfg.get("log_dir", "/var/log/cronwatch")
    path = _audit_path(log_dir, job_name)
    if path.exists():
        os.remove(path)
        click.echo(f"Audit log cleared: {path}")
    else:
        click.echo("No audit log found for that job.", err=True)
        sys.exit(1)

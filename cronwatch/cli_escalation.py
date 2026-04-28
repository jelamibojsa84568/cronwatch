"""CLI commands for inspecting and managing escalation state."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from cronwatch.config import load_config
from cronwatch.escalation import (
    _load_state,
    _state_path,
    get_escalation_policy,
    record_success,
)


@click.group("escalation")
def escalation() -> None:
    """Manage alert escalation state."""


@escalation.command("show")
@click.argument("job_name")
@click.option("--config", "config_path", default=None)
def cmd_show_escalation(job_name: str, config_path: str | None) -> None:
    """Show escalation policy and current state for JOB_NAME."""
    config = load_config(config_path)
    jobs = {j["name"]: j for j in config.get("jobs", [])}
    if job_name not in jobs:
        click.echo(f"Unknown job: {job_name}", err=True)
        sys.exit(1)

    job = jobs[job_name]
    policy = get_escalation_policy(job, config)

    state_dir = Path(config.get("log_dir", "/var/log/cronwatch")) / "escalation"
    state = _load_state(_state_path(state_dir, job_name))

    click.echo(f"Job             : {job_name}")
    click.echo(f"Enabled         : {policy['enabled']}")
    click.echo(f"Threshold       : {policy['threshold']} consecutive failures")
    click.echo(f"Interval        : {policy['interval']}s between escalations")
    click.echo(f"Current failures: {state.get('consecutive_failures', 0)}")
    last = state.get("last_escalated", 0.0)
    click.echo(f"Last escalated  : {last if last else 'never'}")


@escalation.command("reset")
@click.argument("job_name")
@click.option("--config", "config_path", default=None)
def cmd_reset_escalation(job_name: str, config_path: str | None) -> None:
    """Reset the consecutive failure counter for JOB_NAME."""
    config = load_config(config_path)
    jobs = {j["name"]: j for j in config.get("jobs", [])}
    if job_name not in jobs:
        click.echo(f"Unknown job: {job_name}", err=True)
        sys.exit(1)

    state_dir = Path(config.get("log_dir", "/var/log/cronwatch")) / "escalation"
    record_success(state_dir, job_name)
    click.echo(f"Escalation state reset for '{job_name}'.")


@escalation.command("status")
@click.option("--config", "config_path", default=None)
def cmd_escalation_status(config_path: str | None) -> None:
    """List escalation state for all configured jobs."""
    config = load_config(config_path)
    jobs = config.get("jobs", [])
    if not jobs:
        click.echo("No jobs configured.")
        return

    state_dir = Path(config.get("log_dir", "/var/log/cronwatch")) / "escalation"
    rows = []
    for job in jobs:
        name = job["name"]
        state = _load_state(_state_path(state_dir, name))
        rows.append((name, state.get("consecutive_failures", 0)))

    max_len = max(len(r[0]) for r in rows)
    click.echo(f"{'Job':<{max_len}}  Consecutive Failures")
    click.echo("-" * (max_len + 22))
    for name, failures in rows:
        click.echo(f"{name:<{max_len}}  {failures}")

"""CLI commands for inspecting maintenance windows."""

from __future__ import annotations

from datetime import datetime

import click

from cronwatch.config import load_config
from cronwatch.maintenance import is_in_maintenance, parse_maintenance_windows
from cronwatch.scheduler import parse_jobs


@click.group("maintenance")
def maintenance():
    """Inspect and test maintenance window configuration."""


@maintenance.command("status")
@click.option("--config", "config_path", default=None, help="Path to config file.")
def cmd_maintenance_status(config_path: str | None):
    """Show whether any maintenance window is currently active."""
    config = load_config(config_path)
    jobs = parse_jobs(config)
    now = datetime.now()
    any_active = False
    for job in jobs:
        if is_in_maintenance(job, config, now=now):
            click.echo(f"  [ACTIVE]   {job['name']}")
            any_active = True
        else:
            click.echo(f"  [inactive] {job['name']}")
    if not jobs:
        global_windows = parse_maintenance_windows(config.get("maintenance", []))
        if any(w.is_active(now) for w in global_windows):
            click.echo("Global maintenance window is ACTIVE.")
            any_active = True
        else:
            click.echo("No jobs configured.")
    if any_active:
        raise SystemExit(0)


@maintenance.command("show")
@click.argument("job_name")
@click.option("--config", "config_path", default=None, help="Path to config file.")
def cmd_show_maintenance(job_name: str, config_path: str | None):
    """Show maintenance windows configured for a specific job."""
    config = load_config(config_path)
    jobs = {j["name"]: j for j in parse_jobs(config)}
    if job_name not in jobs:
        click.echo(f"Unknown job: {job_name}", err=True)
        raise SystemExit(1)
    job = jobs[job_name]
    global_windows = parse_maintenance_windows(config.get("maintenance", []))
    job_windows = parse_maintenance_windows(job.get("maintenance", []))
    if not global_windows and not job_windows:
        click.echo(f"No maintenance windows configured for '{job_name}'.")
        return
    if global_windows:
        click.echo("Global windows:")
        for w in global_windows:
            click.echo(f"  {w}")
    if job_windows:
        click.echo(f"Job-level windows for '{job_name}':")
        for w in job_windows:
            click.echo(f"  {w}")


@maintenance.command("check")
@click.argument("job_name")
@click.option("--config", "config_path", default=None, help="Path to config file.")
def cmd_check_maintenance(job_name: str, config_path: str | None):
    """Exit 0 if job is in maintenance, 1 otherwise (for scripting)."""
    config = load_config(config_path)
    jobs = {j["name"]: j for j in parse_jobs(config)}
    if job_name not in jobs:
        click.echo(f"Unknown job: {job_name}", err=True)
        raise SystemExit(2)
    active = is_in_maintenance(jobs[job_name], config)
    click.echo("active" if active else "inactive")
    raise SystemExit(0 if active else 1)

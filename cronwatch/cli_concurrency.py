"""CLI sub-commands for inspecting concurrency state."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import click

from cronwatch.concurrency import (
    ConcurrencyPolicy,
    get_concurrency_policy,
    _state_path,
    _load_active,
)
from cronwatch.config import load_config
from cronwatch.scheduler import parse_jobs


@click.group("concurrency")
def concurrency() -> None:
    """Inspect and manage job concurrency limits."""


@concurrency.command("show")
@click.argument("job_name")
@click.option("--config", "config_path", default=None, help="Path to config file.")
def cmd_show_concurrency(job_name: str, config_path: str | None) -> None:
    """Show the concurrency policy for a specific job."""
    cfg = load_config(config_path)
    jobs = parse_jobs(cfg)
    match = next((j for j in jobs if j["name"] == job_name), None)
    if match is None:
        click.echo(f"Unknown job: {job_name}", err=True)
        sys.exit(1)

    pol = get_concurrency_policy(match, cfg)
    click.echo(f"Job          : {job_name}")
    click.echo(f"Max instances: {pol.max_instances} ({'unlimited' if not pol.is_limited() else 'limited'})")
    click.echo(f"State dir    : {pol.state_dir}")


@concurrency.command("status")
@click.option("--config", "config_path", default=None, help="Path to config file.")
def cmd_concurrency_status(config_path: str | None) -> None:
    """Show active instance counts for all jobs."""
    cfg = load_config(config_path)
    jobs = parse_jobs(cfg)

    if not jobs:
        click.echo("No jobs configured.")
        return

    rows = []
    for job in jobs:
        pol = get_concurrency_policy(job, cfg)
        path = _state_path(pol, job["name"])
        active = _load_active(path)
        limit = str(pol.max_instances) if pol.is_limited() else "∞"
        rows.append((job["name"], len(active), limit))

    name_w = max(len(r[0]) for r in rows)
    click.echo(f"{'JOB':<{name_w}}  ACTIVE  LIMIT")
    click.echo("-" * (name_w + 14))
    for name, active, limit in rows:
        click.echo(f"{name:<{name_w}}  {active:<6}  {limit}")


@concurrency.command("clear")
@click.argument("job_name")
@click.option("--config", "config_path", default=None, help="Path to config file.")
def cmd_clear_concurrency(job_name: str, config_path: str | None) -> None:
    """Clear the concurrency state file for a job (use after a crash)."""
    cfg = load_config(config_path)
    jobs = parse_jobs(cfg)
    match = next((j for j in jobs if j["name"] == job_name), None)
    if match is None:
        click.echo(f"Unknown job: {job_name}", err=True)
        sys.exit(1)

    pol = get_concurrency_policy(match, cfg)
    path = _state_path(pol, job_name)
    if path.exists():
        path.unlink()
        click.echo(f"Cleared concurrency state for '{job_name}'.")
    else:
        click.echo(f"No concurrency state found for '{job_name}'.")

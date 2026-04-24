"""CLI commands for inspecting and managing rate limit state."""

from __future__ import annotations

import sys

import click

from cronwatch.config import load_config
from cronwatch.rate_limit import (
    check_rate_limit,
    get_rate_limit_policy,
    record_run,
)
from cronwatch.scheduler import parse_jobs


@click.group("rate-limit")
def rate_limit() -> None:
    """Manage rate limiting for cron jobs."""


@rate_limit.command("show")
@click.argument("job_name")
@click.option("--config", "config_path", default=None, help="Path to config file.")
def cmd_show_rate_limit(job_name: str, config_path: str | None) -> None:
    """Show the rate limit policy for a job."""
    config = load_config(config_path)
    jobs = parse_jobs(config)
    job = next((j for j in jobs if j["name"] == job_name), None)
    if job is None:
        click.echo(f"Unknown job: {job_name}", err=True)
        sys.exit(1)

    policy = get_rate_limit_policy(job, config)
    click.echo(f"Job:    {job_name}")
    click.echo(f"Policy: {policy}")


@rate_limit.command("status")
@click.argument("job_name")
@click.option("--config", "config_path", default=None, help="Path to config file.")
def cmd_rate_limit_status(job_name: str, config_path: str | None) -> None:
    """Check whether a job is currently rate-limited."""
    config = load_config(config_path)
    jobs = parse_jobs(config)
    job = next((j for j in jobs if j["name"] == job_name), None)
    if job is None:
        click.echo(f"Unknown job: {job_name}", err=True)
        sys.exit(1)

    policy = get_rate_limit_policy(job, config)
    state_dir = config.get("state_dir", "/var/lib/cronwatch")
    limited, remaining = check_rate_limit(policy, state_dir, job_name)

    if not policy.is_limited():
        click.echo(f"{job_name}: rate limiting disabled")
    elif limited:
        click.echo(f"{job_name}: RATE LIMITED — {remaining}s remaining")
        sys.exit(1)
    else:
        click.echo(f"{job_name}: OK (not rate limited)")


@rate_limit.command("reset")
@click.argument("job_name")
@click.option("--config", "config_path", default=None, help="Path to config file.")
def cmd_reset_rate_limit(job_name: str, config_path: str | None) -> None:
    """Clear rate limit state for a job so it can run immediately."""
    config = load_config(config_path)
    state_dir = config.get("state_dir", "/var/lib/cronwatch")

    from cronwatch.rate_limit import _state_path
    path = _state_path(state_dir, job_name)
    if path.exists():
        path.unlink()
        click.echo(f"Rate limit state cleared for: {job_name}")
    else:
        click.echo(f"No rate limit state found for: {job_name}")

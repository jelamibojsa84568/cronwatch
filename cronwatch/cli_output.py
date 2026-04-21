"""CLI commands for inspecting output-capture configuration."""

from __future__ import annotations

import sys

import click

from cronwatch.config import load_config
from cronwatch.output_capture import get_capture_policy
from cronwatch.scheduler import parse_jobs


@click.group("output")
def output() -> None:
    """Manage and inspect output-capture settings."""


@output.command("show")
@click.argument("job_name")
@click.option("--config", "config_path", default=None, help="Path to config file.")
def cmd_show_capture(job_name: str, config_path: str | None) -> None:
    """Show the effective output-capture policy for JOB_NAME."""
    config = load_config(config_path)
    jobs = parse_jobs(config)
    job = next((j for j in jobs if j["name"] == job_name), None)
    if job is None:
        click.echo(f"[error] unknown job: {job_name}", err=True)
        sys.exit(1)

    policy = get_capture_policy(job, config)
    click.echo(f"Job            : {job_name}")
    click.echo(f"capture_stdout : {policy.capture_stdout}")
    click.echo(f"capture_stderr : {policy.capture_stderr}")
    click.echo(f"max_bytes      : {policy.max_bytes}")
    click.echo(f"include_in_alerts: {policy.include_in_alerts}")


@output.command("list")
@click.option("--config", "config_path", default=None, help="Path to config file.")
def cmd_list_capture(config_path: str | None) -> None:
    """List output-capture policies for all configured jobs."""
    config = load_config(config_path)
    jobs = parse_jobs(config)
    if not jobs:
        click.echo("No jobs configured.")
        return

    header = f"{'JOB':<30} {'STDOUT':<8} {'STDERR':<8} {'MAX_BYTES':<12} {'IN_ALERTS'}"
    click.echo(header)
    click.echo("-" * len(header))
    for job in jobs:
        p = get_capture_policy(job, config)
        click.echo(
            f"{job['name']:<30} {str(p.capture_stdout):<8} "
            f"{str(p.capture_stderr):<8} {p.max_bytes:<12} {p.include_in_alerts}"
        )

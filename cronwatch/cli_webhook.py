"""CLI commands for inspecting and testing webhook configuration."""

from __future__ import annotations

import sys
import click

from cronwatch.config import load_config
from cronwatch.webhook import get_webhook_policy, send_webhook
from cronwatch.runner import JobResult


@click.group()
def webhook() -> None:
    """Webhook notification commands."""


@webhook.command("show")
@click.argument("job_name")
@click.option("--config", "config_path", default=None)
def cmd_show_webhook(job_name: str, config_path: str | None) -> None:
    """Show the resolved webhook policy for a job."""
    config = load_config(config_path)
    jobs = {j["name"]: j for j in config.get("jobs", [])}
    if job_name not in jobs:
        click.echo(f"Unknown job: {job_name}", err=True)
        sys.exit(1)
    policy = get_webhook_policy(jobs[job_name], config)
    click.echo(repr(policy))
    click.echo(f"  enabled : {policy.is_enabled()}")


@webhook.command("test")
@click.argument("job_name")
@click.option("--config", "config_path", default=None)
@click.option("--success", "simulate_success", is_flag=True, default=False,
              help="Simulate a successful result instead of a failure.")
def cmd_test_webhook(job_name: str, config_path: str | None, simulate_success: bool) -> None:
    """Send a test webhook payload for a job."""
    config = load_config(config_path)
    jobs = {j["name"]: j for j in config.get("jobs", [])}
    if job_name not in jobs:
        click.echo(f"Unknown job: {job_name}", err=True)
        sys.exit(1)

    policy = get_webhook_policy(jobs[job_name], config)
    if not policy.url:
        click.echo("No webhook URL configured for this job.", err=True)
        sys.exit(1)

    exit_code = 0 if simulate_success else 1
    fake_result = JobResult(
        job_name=job_name,
        exit_code=exit_code,
        stdout="test stdout",
        stderr="" if simulate_success else "test stderr",
        duration=0.0,
        started_at="",
    )

    # Temporarily force the policy to fire regardless of on_failure/on_success flags
    from dataclasses import replace
    test_policy = replace(policy, on_failure=True, on_success=True)

    ok = send_webhook(fake_result, test_policy)
    if ok:
        click.echo(f"Webhook delivered successfully to {policy.url}")
    else:
        click.echo(f"Webhook delivery FAILED to {policy.url}", err=True)
        sys.exit(1)

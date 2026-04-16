"""CLI commands for retry-aware job execution."""
from __future__ import annotations

import click

from cronwatch.config import load_config
from cronwatch.history import record_result
from cronwatch.logger import setup_job_logger, log_job_result
from cronwatch.notifier import build_failure_email, send_email_alert
from cronwatch.retry import get_retry_policy, run_with_retry
from cronwatch.scheduler import parse_jobs
from cronwatch.watcher import _send


@click.group()
def retry():
    """Retry-aware job execution commands."""


@retry.command("run")
@click.argument("job_name")
@click.option("--config", "config_path", default=None, help="Path to config file.")
@click.option("--max-attempts", default=None, type=int, help="Override max retry attempts.")
@click.option("--delay", default=None, type=float, help="Override delay between retries (seconds).")
def cmd_retry_run(job_name, config_path, max_attempts, delay):
    """Run a named job with retry logic."""
    config = load_config(config_path)
    jobs = parse_jobs(config)
    job = next((j for j in jobs if j["name"] == job_name), None)
    if job is None:
        raise click.ClickException(f"Job {job_name!r} not found in config.")

    policy = get_retry_policy(job, config)
    if max_attempts is not None:
        policy.max_attempts = max_attempts
    if delay is not None:
        policy.delay_seconds = delay

    click.echo(f"Running {job_name!r} (max {policy.max_attempts} attempts) ...")
    outcome = run_with_retry(job, policy)

    logger = setup_job_logger(job_name, config.get("log_dir", "/var/log/cronwatch"))
    log_job_result(logger, outcome.final_result)
    record_result(outcome.final_result, config.get("log_dir", "/var/log/cronwatch"))

    if outcome.succeeded:
        click.echo(f"✓ {job_name} succeeded after {outcome.attempts} attempt(s).")
    else:
        click.echo(
            f"✗ {job_name} failed after {outcome.attempts} attempt(s).",
            err=True,
        )
        email_cfg = config.get("email")
        if email_cfg:
            msg = build_failure_email(outcome.final_result, email_cfg)
            send_email_alert(msg, email_cfg)
        raise SystemExit(1)

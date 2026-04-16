"""CLI commands for timeout-aware job execution."""
from __future__ import annotations
import sys
import click
from cronwatch.config import load_config
from cronwatch.scheduler import parse_jobs
from cronwatch.runner import run_job
from cronwatch.watcher import _send
from cronwatch.timeout import get_timeout_policy, timeout_context, JobTimeoutError
from cronwatch.history import record_result
from cronwatch.runner import JobResult
import time


@click.group()
def timeout():
    """Timeout-aware job execution commands."""


@timeout.command("run")
@click.argument("job_name")
@click.option("--config", "config_path", default=None)
@click.option("--timeout", "override_timeout", default=None, type=int,
              help="Override timeout in seconds.")
def cmd_timeout_run(job_name: str, config_path: str | None, override_timeout: int | None):
    """Run a job with timeout enforcement."""
    cfg = load_config(config_path)
    jobs = parse_jobs(cfg)
    match = next((j for j in jobs if j["name"] == job_name), None)
    if match is None:
        click.echo(f"Unknown job: {job_name}", err=True)
        sys.exit(2)

    if override_timeout is not None:
        match = {**match, "timeout": override_timeout}

    policy = get_timeout_policy(match, cfg)
    click.echo(f"Running '{job_name}' with timeout={policy.seconds}s ...")

    start = time.time()
    try:
        with timeout_context(job_name, policy):
            result = run_job(match, cfg)
    except JobTimeoutError as exc:
        elapsed = time.time() - start
        click.echo(f"TIMEOUT: {exc}", err=True)
        result = JobResult(
            job_name=job_name,
            command=match.get("command", ""),
            exit_code=124,
            stdout="",
            stderr=f"Timed out after {policy.seconds}s",
            duration=elapsed,
        )

    record_result(result, cfg)
    if not result.success:
        _send(result, cfg)
        click.echo(f"FAILED: {result}", err=True)
        sys.exit(1)
    click.echo(f"OK: {result}")

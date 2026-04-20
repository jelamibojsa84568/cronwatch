"""CLI commands for inspecting and testing hook configuration."""

from __future__ import annotations

import click

from cronwatch.config import load_config
from cronwatch.hooks import get_hook_policy, run_hooks
from cronwatch.scheduler import parse_jobs


@click.group("hooks")
def hooks():
    """Manage and test pre/post job hooks."""


@hooks.command("show")
@click.argument("job_name")
@click.option("--config", "config_path", default=None, help="Path to config file.")
def cmd_show_hooks(job_name: str, config_path: str | None):
    """Display the hook configuration for a specific job."""
    cfg = load_config(config_path)
    jobs = parse_jobs(cfg)
    job = next((j for j in jobs if j["name"] == job_name), None)
    if job is None:
        click.echo(f"Job '{job_name}' not found.", err=True)
        raise SystemExit(1)

    policy = get_hook_policy(job, cfg)
    click.echo(f"Hooks for job: {job_name}")
    click.echo(f"  pre       : {policy.pre or '(none)'}")
    click.echo(f"  post      : {policy.post or '(none)'}")
    click.echo(f"  on_failure: {policy.on_failure or '(none)'}")
    click.echo(f"  timeout   : {policy.timeout}s")


@hooks.command("test")
@click.argument("job_name")
@click.option("--phase", type=click.Choice(["pre", "post", "on_failure"]), default="pre")
@click.option("--config", "config_path", default=None, help="Path to config file.")
def cmd_test_hooks(job_name: str, phase: str, config_path: str | None):
    """Run hooks for a specific phase of a job and report results."""
    cfg = load_config(config_path)
    jobs = parse_jobs(cfg)
    job = next((j for j in jobs if j["name"] == job_name), None)
    if job is None:
        click.echo(f"Job '{job_name}' not found.", err=True)
        raise SystemExit(1)

    policy = get_hook_policy(job, cfg)
    commands = getattr(policy, phase)
    if not commands:
        click.echo(f"No '{phase}' hooks configured for job '{job_name}'.")
        return

    click.echo(f"Running {len(commands)} '{phase}' hook(s) for '{job_name}'...")
    results = run_hooks(commands, policy.timeout, phase)
    all_ok = all(results)
    for cmd, ok in zip(commands, results):
        status = click.style("OK", fg="green") if ok else click.style("FAIL", fg="red")
        click.echo(f"  [{status}] {cmd}")

    if not all_ok:
        raise SystemExit(1)

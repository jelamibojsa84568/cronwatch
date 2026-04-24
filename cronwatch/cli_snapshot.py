"""CLI commands for job snapshot management."""

from __future__ import annotations

import sys

import click

from cronwatch.config import load_config
from cronwatch.scheduler import parse_jobs
from cronwatch.snapshot import (
    capture_snapshot,
    diff_snapshots,
    format_diff_text,
    load_snapshot,
)


@click.group()
def snapshot() -> None:
    """Commands for capturing and comparing job snapshots."""


@snapshot.command("capture")
@click.option("--config", "config_path", default=None, help="Path to config file.")
def cmd_capture(config_path: str | None) -> None:
    """Capture the current job configuration as a snapshot."""
    cfg = load_config(config_path)
    jobs = parse_jobs(cfg)
    log_dir = cfg.get("log_dir", "/var/log/cronwatch")
    snap = capture_snapshot(jobs, log_dir)
    count = len(snap["jobs"])
    click.echo(f"Snapshot captured: {count} job(s) recorded.")


@snapshot.command("diff")
@click.option("--config", "config_path", default=None, help="Path to config file.")
def cmd_diff(config_path: str | None) -> None:
    """Compare the current job config against the last saved snapshot."""
    cfg = load_config(config_path)
    log_dir = cfg.get("log_dir", "/var/log/cronwatch")
    old = load_snapshot(log_dir)
    if old is None:
        click.echo("No previous snapshot found. Run 'snapshot capture' first.")
        sys.exit(1)
    jobs = parse_jobs(cfg)
    new_snap = {"jobs": {}}
    for job in jobs:
        from cronwatch.snapshot import _job_fingerprint
        new_snap["jobs"][job["name"]] = {
            "schedule": job.get("schedule"),
            "command": job.get("command"),
            "fingerprint": _job_fingerprint(job),
        }
    diff = diff_snapshots(old, new_snap)
    click.echo(format_diff_text(diff))


@snapshot.command("show")
@click.option("--config", "config_path", default=None, help="Path to config file.")
def cmd_show(config_path: str | None) -> None:
    """Display the most recently captured snapshot."""
    cfg = load_config(config_path)
    log_dir = cfg.get("log_dir", "/var/log/cronwatch")
    snap = load_snapshot(log_dir)
    if snap is None:
        click.echo("No snapshot found.")
        sys.exit(1)
    import datetime
    ts = datetime.datetime.fromtimestamp(snap["captured_at"]).strftime("%Y-%m-%d %H:%M:%S")
    click.echo(f"Snapshot from {ts}:")
    for name, info in sorted(snap["jobs"].items()):
        click.echo(f"  {name}: schedule={info['schedule']}  command={info['command']}")

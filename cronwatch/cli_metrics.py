"""CLI commands for job execution metrics."""

from __future__ import annotations

import sys

import click

from cronwatch.config import load_config
from cronwatch.metrics import compute_metrics, format_metrics_text, load_metrics, save_metrics
from cronwatch.scheduler import parse_jobs


@click.group("metrics")
def metrics() -> None:
    """Job execution metrics commands."""


@metrics.command("show")
@click.argument("job_name")
@click.option("--config", "config_path", default=None, help="Path to config file.")
@click.option("--window", default=50, show_default=True, help="History entries to consider.")
@click.option("--save", is_flag=True, default=False, help="Persist snapshot to disk.")
def cmd_show_metrics(job_name: str, config_path: str | None, window: int, save: bool) -> None:
    """Display execution metrics for JOB_NAME."""
    cfg = load_config(config_path)
    history_dir = cfg.get("history_dir", "/var/log/cronwatch/history")
    metrics_dir = cfg.get("metrics_dir", "/var/log/cronwatch/metrics")

    m = compute_metrics(job_name, history_dir, window=window)
    click.echo(format_metrics_text(m))

    if save:
        save_metrics(m, metrics_dir)
        click.echo(f"\nMetrics saved to {metrics_dir}")


@metrics.command("all")
@click.option("--config", "config_path", default=None, help="Path to config file.")
@click.option("--window", default=50, show_default=True, help="History entries to consider.")
@click.option("--save", is_flag=True, default=False, help="Persist snapshots to disk.")
def cmd_all_metrics(config_path: str | None, window: int, save: bool) -> None:
    """Display metrics for every configured job."""
    cfg = load_config(config_path)
    history_dir = cfg.get("history_dir", "/var/log/cronwatch/history")
    metrics_dir = cfg.get("metrics_dir", "/var/log/cronwatch/metrics")

    jobs = parse_jobs(cfg)
    if not jobs:
        click.echo("No jobs configured.")
        return

    for job in jobs:
        m = compute_metrics(job["name"], history_dir, window=window)
        click.echo(format_metrics_text(m))
        click.echo("")
        if save:
            save_metrics(m, metrics_dir)

    if save:
        click.echo(f"Metrics saved to {metrics_dir}")


@metrics.command("cached")
@click.argument("job_name")
@click.option("--config", "config_path", default=None, help="Path to config file.")
def cmd_cached_metrics(job_name: str, config_path: str | None) -> None:
    """Show the last persisted metrics snapshot for JOB_NAME."""
    cfg = load_config(config_path)
    metrics_dir = cfg.get("metrics_dir", "/var/log/cronwatch/metrics")

    m = load_metrics(job_name, metrics_dir)
    if m is None:
        click.echo(f"No cached metrics found for '{job_name}'.")
        sys.exit(1)

    click.echo(format_metrics_text(m))
    click.echo(f"\n(computed at {m.get('computed_at')})")  

"""
cronwatch/cli_labels.py

CLI commands for working with job labels.
"""
import sys
import click

from cronwatch.config import load_config
from cronwatch.scheduler import parse_jobs
from cronwatch.labels import (
    filter_jobs_by_labels,
    list_all_label_keys,
    build_label_index,
)


@click.group("labels")
def labels() -> None:
    """Commands for job labels."""


@labels.command("list-keys")
@click.option("--config", "config_path", default=None, help="Path to config file.")
def cmd_list_keys(config_path: str) -> None:
    """List every label key defined across all jobs."""
    cfg = load_config(config_path)
    jobs = parse_jobs(cfg)
    keys = list_all_label_keys(jobs)
    if not keys:
        click.echo("No labels defined.")
        return
    for key in keys:
        click.echo(key)


@labels.command("filter")
@click.argument("label_pairs", nargs=-1, metavar="KEY=VALUE ...")
@click.option("--config", "config_path", default=None, help="Path to config file.")
def cmd_filter_jobs(label_pairs: tuple, config_path: str) -> None:
    """List jobs matching ALL provided KEY=VALUE label pairs."""
    match = {}
    for pair in label_pairs:
        if "=" not in pair:
            click.echo(f"Invalid label pair '{pair}' — expected KEY=VALUE", err=True)
            sys.exit(1)
        k, v = pair.split("=", 1)
        match[k.strip()] = v.strip()

    cfg = load_config(config_path)
    jobs = parse_jobs(cfg)
    matched = filter_jobs_by_labels(jobs, match)
    if not matched:
        click.echo("No jobs match the given labels.")
        return
    for job in matched:
        click.echo(job["name"])


@labels.command("index")
@click.option("--config", "config_path", default=None, help="Path to config file.")
def cmd_label_index(config_path: str) -> None:
    """Show a grouped index of all labels and the jobs that carry them."""
    cfg = load_config(config_path)
    jobs = parse_jobs(cfg)
    index = build_label_index(jobs)
    if not index:
        click.echo("No labels defined.")
        return
    for key in sorted(index):
        click.echo(f"[{key}]")
        for value in sorted(index[key]):
            job_list = ", ".join(sorted(index[key][value]))
            click.echo(f"  {value}: {job_list}")

"""CLI commands for tag-based filtering and reporting."""
import click
from cronwatch.config import load_config
from cronwatch.scheduler import parse_jobs
from cronwatch.tags import filter_jobs_by_tags, list_all_tags
from cronwatch.tag_report import build_tag_report, format_tag_report


@click.group()
def tags():
    """Tag-based job filtering and reporting."""


@tags.command("list")
@click.option("--config", "config_path", default=None, help="Path to config file.")
def cmd_list_tags(config_path):
    """List all unique tags defined across jobs."""
    cfg = load_config(config_path)
    jobs = parse_jobs(cfg)
    all_tags = list_all_tags(jobs)
    if not all_tags:
        click.echo("No tags found.")
        return
    for tag in all_tags:
        click.echo(tag)


@tags.command("filter")
@click.option("--config", "config_path", default=None)
@click.option("--include", multiple=True, help="Only jobs with this tag.")
@click.option("--exclude", multiple=True, help="Omit jobs with this tag.")
def cmd_filter_jobs(config_path, include, exclude):
    """List job names matching tag filters."""
    cfg = load_config(config_path)
    jobs = parse_jobs(cfg)
    filtered = filter_jobs_by_tags(
        jobs,
        include=list(include) or None,
        exclude=list(exclude) or None,
    )
    if not filtered:
        click.echo("No jobs match the given filters.")
        return
    for job in filtered:
        tags_str = ", ".join(job.get("tags", []))
        click.echo(f"{job['name']:<30} [{tags_str}]")


@tags.command("report")
@click.option("--config", "config_path", default=None)
@click.option("--limit", default=50, show_default=True, help="Max history entries per job.")
def cmd_tag_report(config_path, limit):
    """Show run/failure summary grouped by tag."""
    cfg = load_config(config_path)
    jobs = parse_jobs(cfg)
    history_dir = cfg.get("history_dir", "/var/log/cronwatch/history")
    summary = build_tag_report(jobs, history_dir=history_dir, limit=limit)
    click.echo(format_tag_report(summary))

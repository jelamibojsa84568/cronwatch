"""Generate summary reports of cron job activity over a time window."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from cronwatch.history import get_history


def _parse_window(window: str) -> timedelta:
    """Parse a window string like '1h', '24h', '7d' into a timedelta."""
    unit = window[-1]
    try:
        value = int(window[:-1])
    except ValueError:
        raise ValueError(f"Invalid window format: {window!r}. Expected e.g. '1h', '24h', '7d'.")
    if unit == 'h':
        return timedelta(hours=value)
    elif unit == 'd':
        return timedelta(days=value)
    raise ValueError(f"Unknown time unit {unit!r}. Use 'h' for hours or 'd' for days.")


def build_report(jobs: list[dict[str, Any]], history_dir: str, window: str = "24h") -> dict[str, Any]:
    """Build a summary report for all jobs within the given time window.

    Returns a dict with overall stats and per-job breakdowns.
    """
    delta = _parse_window(window)
    cutoff = datetime.utcnow() - delta

    total_runs = 0
    total_failures = 0
    job_stats: list[dict[str, Any]] = []

    for job in jobs:
        name = job["name"]
        entries = [
            e for e in get_history(name, history_dir)
            if datetime.fromisoformat(e["timestamp"]) >= cutoff
        ]
        runs = len(entries)
        failures = sum(1 for e in entries if not e.get("success", True))
        last_run = entries[-1]["timestamp"] if entries else None

        total_runs += runs
        total_failures += failures
        job_stats.append({
            "name": name,
            "runs": runs,
            "failures": failures,
            "success_rate": round((runs - failures) / runs * 100, 1) if runs else None,
            "last_run": last_run,
        })

    return {
        "window": window,
        "generated_at": datetime.utcnow().isoformat(),
        "total_runs": total_runs,
        "total_failures": total_failures,
        "jobs": job_stats,
    }


def format_report_text(report: dict[str, Any]) -> str:
    """Format a report dict as a human-readable text summary."""
    lines = [
        f"CronWatch Report — window: {report['window']}",
        f"Generated: {report['generated_at']}",
        f"Total runs: {report['total_runs']}  |  Total failures: {report['total_failures']}",
        "-" * 60,
    ]
    for job in report["jobs"]:
        rate = f"{job['success_rate']}%" if job["success_rate"] is not None else "N/A"
        last = job["last_run"] or "never"
        lines.append(
            f"  {job['name']:<30} runs={job['runs']}  failures={job['failures']}  "
            f"success={rate}  last={last}"
        )
    lines.append("-" * 60)
    return "\n".join(lines)

"""janitor.py — Prune stale log files and history entries beyond retention limits."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional

DEFAULT_LOG_MAX_AGE_DAYS = 30
DEFAULT_HISTORY_MAX_AGE_DAYS = 90
DEFAULT_METRICS_MAX_AGE_DAYS = 90


def get_janitor_policy(config: dict) -> dict:
    """Return the janitor retention policy merged from global config."""
    raw = config.get("janitor", {})
    return {
        "log_max_age_days": int(
            raw.get("log_max_age_days", DEFAULT_LOG_MAX_AGE_DAYS)
        ),
        "history_max_age_days": int(
            raw.get("history_max_age_days", DEFAULT_HISTORY_MAX_AGE_DAYS)
        ),
        "metrics_max_age_days": int(
            raw.get("metrics_max_age_days", DEFAULT_METRICS_MAX_AGE_DAYS)
        ),
        "dry_run": bool(raw.get("dry_run", False)),
    }


def _prune_directory(
    directory: Path,
    max_age_days: int,
    suffix_filter: Optional[str],
    dry_run: bool,
) -> list[str]:
    """Delete files older than *max_age_days* inside *directory*.

    Returns list of paths that were (or would be) removed.
    """
    removed: list[str] = []
    if not directory.is_dir():
        return removed

    cutoff = time.time() - max_age_days * 86400
    for entry in directory.iterdir():
        if not entry.is_file():
            continue
        if suffix_filter and not entry.name.endswith(suffix_filter):
            continue
        if entry.stat().st_mtime < cutoff:
            removed.append(str(entry))
            if not dry_run:
                entry.unlink(missing_ok=True)
    return removed


def run_janitor(config: dict) -> dict:
    """Run all pruning tasks and return a summary dict.

    Summary keys: ``logs``, ``history``, ``metrics`` — each a list of
    removed (or would-be-removed) file paths.
    """
    policy = get_janitor_policy(config)
    dry_run = policy["dry_run"]

    log_dir = Path(config.get("log_dir", "/var/log/cronwatch"))
    history_dir = Path(config.get("history_dir", "/var/lib/cronwatch/history"))
    metrics_dir = Path(config.get("metrics_dir", "/var/lib/cronwatch/metrics"))

    return {
        "logs": _prune_directory(log_dir, policy["log_max_age_days"], ".log", dry_run),
        "history": _prune_directory(
            history_dir, policy["history_max_age_days"], ".jsonl", dry_run
        ),
        "metrics": _prune_directory(
            metrics_dir, policy["metrics_max_age_days"], ".json", dry_run
        ),
    }

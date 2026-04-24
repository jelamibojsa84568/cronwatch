"""Job execution metrics: track run counts, durations, and success rates."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from cronwatch.history import get_history


def _metrics_path(metrics_dir: str, job_name: str) -> Path:
    safe = job_name.replace("/", "_").replace(" ", "_")
    return Path(metrics_dir) / f"{safe}.metrics.json"


def compute_metrics(job_name: str, history_dir: str, window: int = 50) -> dict[str, Any]:
    """Compute aggregated metrics for *job_name* from the last *window* history entries."""
    entries = get_history(job_name, history_dir, limit=window)
    if not entries:
        return {
            "job": job_name,
            "runs": 0,
            "successes": 0,
            "failures": 0,
            "success_rate": None,
            "avg_duration": None,
            "min_duration": None,
            "max_duration": None,
            "last_run": None,
            "last_status": None,
        }

    runs = len(entries)
    successes = sum(1 for e in entries if e.get("exit_code", 1) == 0)
    failures = runs - successes
    durations = [e["duration"] for e in entries if "duration" in e and e["duration"] is not None]

    return {
        "job": job_name,
        "runs": runs,
        "successes": successes,
        "failures": failures,
        "success_rate": round(successes / runs * 100, 1) if runs else None,
        "avg_duration": round(sum(durations) / len(durations), 3) if durations else None,
        "min_duration": round(min(durations), 3) if durations else None,
        "max_duration": round(max(durations), 3) if durations else None,
        "last_run": entries[-1].get("timestamp"),
        "last_status": "success" if entries[-1].get("exit_code", 1) == 0 else "failure",
    }


def save_metrics(metrics: dict[str, Any], metrics_dir: str) -> None:
    """Persist *metrics* snapshot to disk."""
    Path(metrics_dir).mkdir(parents=True, exist_ok=True)
    path = _metrics_path(metrics_dir, metrics["job"])
    metrics["computed_at"] = time.time()
    path.write_text(json.dumps(metrics, indent=2))


def load_metrics(job_name: str, metrics_dir: str) -> dict[str, Any] | None:
    """Load the last persisted metrics snapshot for *job_name*, or None."""
    path = _metrics_path(metrics_dir, job_name)
    if not path.exists():
        return None
    return json.loads(path.read_text())


def format_metrics_text(metrics: dict[str, Any]) -> str:
    """Return a human-readable summary of *metrics*."""
    if metrics["runs"] == 0:
        return f"[{metrics['job']}] No history found."
    lines = [
        f"Job          : {metrics['job']}",
        f"Runs         : {metrics['runs']}",
        f"Successes    : {metrics['successes']}",
        f"Failures     : {metrics['failures']}",
        f"Success rate : {metrics['success_rate']}%",
        f"Avg duration : {metrics['avg_duration']}s",
        f"Min duration : {metrics['min_duration']}s",
        f"Max duration : {metrics['max_duration']}s",
        f"Last run     : {metrics['last_run']}",
        f"Last status  : {metrics['last_status']}",
    ]
    return "\n".join(lines)

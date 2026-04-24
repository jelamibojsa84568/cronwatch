"""Job snapshot: capture and compare cron job configurations over time."""

from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any


def _snapshot_path(log_dir: str) -> str:
    return os.path.join(log_dir, "snapshots", "job_snapshot.json")


def _job_fingerprint(job: dict[str, Any]) -> str:
    """Return a stable hash of the job definition."""
    stable = json.dumps(job, sort_keys=True, default=str)
    return hashlib.sha256(stable.encode()).hexdigest()[:16]


def capture_snapshot(jobs: list[dict[str, Any]], log_dir: str) -> dict[str, Any]:
    """Persist a snapshot of the current job list and return it."""
    snapshot = {
        "captured_at": time.time(),
        "jobs": {
            job["name"]: {
                "schedule": job.get("schedule"),
                "command": job.get("command"),
                "fingerprint": _job_fingerprint(job),
            }
            for job in jobs
        },
    }
    path = _snapshot_path(log_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(snapshot, fh, indent=2)
    return snapshot


def load_snapshot(log_dir: str) -> dict[str, Any] | None:
    """Load the most recent snapshot, or None if none exists."""
    path = _snapshot_path(log_dir)
    if not os.path.exists(path):
        return None
    with open(path) as fh:
        return json.load(fh)


def diff_snapshots(
    old: dict[str, Any], new: dict[str, Any]
) -> dict[str, list[str]]:
    """Return added, removed, and changed job names between two snapshots."""
    old_jobs = old.get("jobs", {})
    new_jobs = new.get("jobs", {})

    added = [name for name in new_jobs if name not in old_jobs]
    removed = [name for name in old_jobs if name not in new_jobs]
    changed = [
        name
        for name in new_jobs
        if name in old_jobs
        and new_jobs[name]["fingerprint"] != old_jobs[name]["fingerprint"]
    ]
    return {"added": added, "removed": removed, "changed": changed}


def format_diff_text(diff: dict[str, list[str]]) -> str:
    """Return a human-readable summary of a snapshot diff."""
    lines: list[str] = []
    for label, names in (("Added", diff["added"]), ("Removed", diff["removed"]), ("Changed", diff["changed"])):
        if names:
            lines.append(f"{label}: {', '.join(sorted(names))}")
    return "\n".join(lines) if lines else "No changes detected."

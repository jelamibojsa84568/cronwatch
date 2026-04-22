"""Concurrency limit policy for cron jobs.

Allows capping how many instances of a job (or all jobs) can run
concurrently by tracking active PIDs in a small state file.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class ConcurrencyPolicy:
    max_instances: int = 1  # 0 = unlimited
    state_dir: str = "/tmp/cronwatch/concurrency"

    def is_limited(self) -> bool:
        return self.max_instances > 0


def get_concurrency_policy(job: dict, config: dict) -> ConcurrencyPolicy:
    """Build a ConcurrencyPolicy by merging global config with job-level overrides."""
    global_cc = config.get("concurrency", {})
    job_cc = job.get("concurrency", {})

    # Allow shorthand: concurrency: 3  (just an int)
    if isinstance(global_cc, int):
        global_cc = {"max_instances": global_cc}
    if isinstance(job_cc, int):
        job_cc = {"max_instances": job_cc}

    merged = {**global_cc, **job_cc}
    state_dir = config.get("state_dir", "/tmp/cronwatch/concurrency")
    return ConcurrencyPolicy(
        max_instances=int(merged.get("max_instances", 1)),
        state_dir=merged.get("state_dir", state_dir),
    )


def _state_path(policy: ConcurrencyPolicy, job_name: str) -> Path:
    safe = job_name.replace(" ", "_").replace("/", "_")
    return Path(policy.state_dir) / f"{safe}.json"


def _load_active(path: Path) -> List[int]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        # Prune stale PIDs (process no longer running)
        alive = [pid for pid in data.get("pids", []) if _pid_alive(pid)]
        return alive
    except (json.JSONDecodeError, OSError):
        return []


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _save_active(path: Path, pids: List[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"pids": pids, "updated": time.time()}))


def acquire_slot(policy: ConcurrencyPolicy, job_name: str) -> bool:
    """Try to acquire a concurrency slot for *job_name*.

    Returns True if the slot was acquired (caller should call release_slot
    when done), False if the limit is already reached.
    """
    if not policy.is_limited():
        return True
    path = _state_path(policy, job_name)
    active = _load_active(path)
    if len(active) >= policy.max_instances:
        return False
    active.append(os.getpid())
    _save_active(path, active)
    return True


def release_slot(policy: ConcurrencyPolicy, job_name: str) -> None:
    """Remove the current PID from the active list for *job_name*."""
    path = _state_path(policy, job_name)
    active = _load_active(path)
    pid = os.getpid()
    active = [p for p in active if p != pid]
    _save_active(path, active)

"""Lockfile support to prevent overlapping cron job executions."""

import os
import time
import errno
from dataclasses import dataclass
from typing import Optional


@dataclass
class LockPolicy:
    enabled: bool
    lock_dir: str
    stale_after: int  # seconds; 0 means never treat as stale

    @property
    def is_enabled(self) -> bool:
        return self.enabled


def get_lock_policy(config: dict, job: dict) -> LockPolicy:
    """Resolve lockfile policy from global config and per-job overrides."""
    global_lock = config.get("lockfile", {})
    job_lock = job.get("lockfile", {})

    # A job-level scalar True/False enables/disables with defaults
    if isinstance(job_lock, bool):
        job_lock = {"enabled": job_lock}
    if isinstance(global_lock, bool):
        global_lock = {"enabled": global_lock}

    enabled = job_lock.get("enabled", global_lock.get("enabled", False))
    lock_dir = job_lock.get(
        "lock_dir",
        global_lock.get("lock_dir", "/tmp/cronwatch/locks"),
    )
    stale_after = int(
        job_lock.get("stale_after", global_lock.get("stale_after", 0))
    )
    return LockPolicy(enabled=bool(enabled), lock_dir=lock_dir, stale_after=stale_after)


def _lock_path(lock_dir: str, job_name: str) -> str:
    safe_name = job_name.replace("/", "_").replace(" ", "_")
    return os.path.join(lock_dir, f"{safe_name}.lock")


class LockAcquireError(Exception):
    """Raised when a lock cannot be acquired because another instance is running."""


def acquire_lock(policy: LockPolicy, job_name: str) -> str:
    """Create a lockfile. Returns the lock path on success.

    Raises LockAcquireError if the lock is held and not stale.
    """
    os.makedirs(policy.lock_dir, exist_ok=True)
    path = _lock_path(policy.lock_dir, job_name)

    if os.path.exists(path):
        mtime = os.path.getmtime(path)
        age = time.time() - mtime
        if policy.stale_after > 0 and age > policy.stale_after:
            # Stale lock — remove and proceed
            os.remove(path)
        else:
            with open(path) as fh:
                pid = fh.read().strip()
            raise LockAcquireError(
                f"Job '{job_name}' is already running (pid={pid}, age={int(age)}s)"
            )

    with open(path, "w") as fh:
        fh.write(str(os.getpid()))
    return path


def release_lock(policy: LockPolicy, job_name: str) -> None:
    """Remove the lockfile for a job if it exists."""
    path = _lock_path(policy.lock_dir, job_name)
    try:
        os.remove(path)
    except OSError as exc:
        if exc.errno != errno.ENOENT:
            raise

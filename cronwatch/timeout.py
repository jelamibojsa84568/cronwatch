"""Timeout enforcement for cron job execution."""
from __future__ import annotations
import signal
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Optional


class JobTimeoutError(Exception):
    """Raised when a job exceeds its allowed runtime."""
    def __init__(self, job_name: str, timeout: int):
        self.job_name = job_name
        self.timeout = timeout
        super().__init__(f"Job '{job_name}' timed out after {timeout}s")


@dataclass
class TimeoutPolicy:
    seconds: Optional[int]  # None means no timeout

    def is_enabled(self) -> bool:
        return self.seconds is not None and self.seconds > 0


def get_timeout_policy(job: dict, config: dict) -> TimeoutPolicy:
    """Resolve timeout for a job: job-level > global > None."""
    job_timeout = job.get("timeout")
    if job_timeout is not None:
        return TimeoutPolicy(seconds=int(job_timeout))
    global_timeout = config.get("defaults", {}).get("timeout")
    if global_timeout is not None:
        return TimeoutPolicy(seconds=int(global_timeout))
    return TimeoutPolicy(seconds=None)


@contextmanager
def timeout_context(job_name: str, policy: TimeoutPolicy):
    """Context manager that raises JobTimeoutError if block exceeds policy.seconds."""
    if not policy.is_enabled():
        yield
        return

    def _handler(signum, frame):
        raise JobTimeoutError(job_name, policy.seconds)

    old_handler = signal.signal(signal.SIGALRM, _handler)
    signal.alarm(policy.seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

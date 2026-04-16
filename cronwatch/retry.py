"""Retry logic for failed cron jobs."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from cronwatch.runner import JobResult, run_job


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    delay_seconds: float = 5.0
    backoff_factor: float = 2.0


@dataclass
class RetryOutcome:
    job_name: str
    attempts: int
    final_result: JobResult
    succeeded: bool
    delays: list[float] = field(default_factory=list)

    def __repr__(self) -> str:
        status = "succeeded" if self.succeeded else "failed"
        return f"<RetryOutcome job={self.job_name!r} attempts={self.attempts} {status}>"


def get_retry_policy(job: dict, config: dict) -> RetryPolicy:
    """Build a RetryPolicy from job-level or global config."""
    defaults = config.get("retry", {})
    job_retry = job.get("retry", {})
    merged = {**defaults, **job_retry}
    return RetryPolicy(
        max_attempts=int(merged.get("max_attempts", 3)),
        delay_seconds=float(merged.get("delay_seconds", 5.0)),
        backoff_factor=float(merged.get("backoff_factor", 2.0)),
    )


def run_with_retry(
    job: dict,
    policy: RetryPolicy,
    _sleep=time.sleep,
) -> RetryOutcome:
    """Run a job, retrying on failure according to policy."""
    name = job["name"]
    command = job["command"]
    timeout = job.get("timeout")
    attempts = 0
    delays: list[float] = []
    result: Optional[JobResult] = None
    delay = policy.delay_seconds

    for attempt in range(1, policy.max_attempts + 1):
        attempts = attempt
        result = run_job(name, command, timeout=timeout)
        if result.success:
            return RetryOutcome(
                job_name=name,
                attempts=attempts,
                final_result=result,
                succeeded=True,
                delays=delays,
            )
        if attempt < policy.max_attempts:
            delays.append(delay)
            _sleep(delay)
            delay *= policy.backoff_factor

    return RetryOutcome(
        job_name=name,
        attempts=attempts,
        final_result=result,
        succeeded=False,
        delays=delays,
    )

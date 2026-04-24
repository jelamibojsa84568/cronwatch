"""Rate limiting for cron job execution — prevent jobs from running too frequently."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class RateLimitPolicy:
    enabled: bool
    min_interval: int  # seconds between runs

    def is_limited(self) -> bool:
        return self.enabled and self.min_interval > 0

    def __repr__(self) -> str:
        if not self.is_limited():
            return "RateLimitPolicy(disabled)"
        return f"RateLimitPolicy(min_interval={self.min_interval}s)"


def get_rate_limit_policy(job: dict, config: dict) -> RateLimitPolicy:
    """Resolve rate limit policy from job config, falling back to global config."""
    global_rl = config.get("rate_limit", {})
    job_rl = job.get("rate_limit", {})

    if isinstance(job_rl, int):
        job_rl = {"min_interval": job_rl}
    if isinstance(global_rl, int):
        global_rl = {"min_interval": global_rl}

    min_interval = job_rl.get("min_interval", global_rl.get("min_interval", 0))
    enabled = bool(min_interval)

    return RateLimitPolicy(enabled=enabled, min_interval=int(min_interval))


def _state_path(state_dir: str, job_name: str) -> Path:
    safe = job_name.replace("/", "_").replace(" ", "_")
    return Path(state_dir) / f"ratelimit_{safe}.json"


def _load_last_run(state_dir: str, job_name: str) -> Optional[float]:
    path = _state_path(state_dir, job_name)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return float(data.get("last_run", 0))
    except (json.JSONDecodeError, ValueError):
        return None


def record_run(state_dir: str, job_name: str) -> None:
    """Record that a job ran right now."""
    path = _state_path(state_dir, job_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"last_run": time.time()}))


def check_rate_limit(policy: RateLimitPolicy, state_dir: str, job_name: str) -> tuple[bool, float]:
    """Return (is_rate_limited, seconds_remaining). If not limited, seconds_remaining=0."""
    if not policy.is_limited():
        return False, 0.0

    last_run = _load_last_run(state_dir, job_name)
    if last_run is None:
        return False, 0.0

    elapsed = time.time() - last_run
    remaining = policy.min_interval - elapsed
    if remaining > 0:
        return True, round(remaining, 1)
    return False, 0.0

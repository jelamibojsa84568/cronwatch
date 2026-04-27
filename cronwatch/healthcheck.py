"""Health check endpoint support for cronwatch.

Allows jobs to report liveness via a simple HTTP ping (e.g. healthchecks.io,
BetterUptime, or a self-hosted endpoint).  The policy is read from config and
can be overridden per-job.
"""

from __future__ import annotations

import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class HealthCheckPolicy:
    url: Optional[str] = None          # ping URL; None means disabled
    ping_start: bool = False            # also ping at job start (append /start)
    ping_failure: bool = True           # ping failure endpoint on non-zero exit
    timeout_seconds: int = 10

    def is_enabled(self) -> bool:
        return bool(self.url)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"HealthCheckPolicy(url={self.url!r}, ping_start={self.ping_start}, "
            f"ping_failure={self.ping_failure}, timeout={self.timeout_seconds}s)"
        )


def get_healthcheck_policy(
    config: Dict[str, Any],
    job: Dict[str, Any],
) -> HealthCheckPolicy:
    """Build a HealthCheckPolicy by merging global defaults with job overrides."""
    global_hc: Dict[str, Any] = config.get("healthcheck", {})
    job_hc: Any = job.get("healthcheck", {})

    # Job-level value may be a bare URL string for convenience.
    if isinstance(job_hc, str):
        job_hc = {"url": job_hc}
    elif not isinstance(job_hc, dict):
        job_hc = {}

    merged: Dict[str, Any] = {**global_hc, **job_hc}

    return HealthCheckPolicy(
        url=merged.get("url") or None,
        ping_start=bool(merged.get("ping_start", False)),
        ping_failure=bool(merged.get("ping_failure", True)),
        timeout_seconds=int(merged.get("timeout_seconds", 10)),
    )


def _ping(url: str, timeout: int) -> bool:
    """Send a GET request to *url*.  Returns True on HTTP 2xx, False otherwise."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
            return 200 <= resp.status < 300
    except Exception:  # noqa: BLE001
        return False


def ping_start(policy: HealthCheckPolicy) -> bool:
    """Ping the /start sub-path if configured."""
    if not policy.is_enabled() or not policy.ping_start:
        return False
    url = policy.url.rstrip("/") + "/start"  # type: ignore[union-attr]
    return _ping(url, policy.timeout_seconds)


def ping_success(policy: HealthCheckPolicy) -> bool:
    """Ping the success URL after a successful run."""
    if not policy.is_enabled():
        return False
    return _ping(policy.url, policy.timeout_seconds)  # type: ignore[arg-type]


def ping_failure(policy: HealthCheckPolicy) -> bool:
    """Ping the /fail sub-path after a failed run."""
    if not policy.is_enabled() or not policy.ping_failure:
        return False
    url = policy.url.rstrip("/") + "/fail"  # type: ignore[union-attr]
    return _ping(url, policy.timeout_seconds)

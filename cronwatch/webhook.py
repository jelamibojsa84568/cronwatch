"""Webhook notification support for cronwatch.

Allows jobs to POST a JSON payload to a configured URL on failure (or success).
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Optional

from cronwatch.runner import JobResult


@dataclass
class WebhookPolicy:
    url: Optional[str]
    on_failure: bool
    on_success: bool
    timeout: int
    secret_header: Optional[str]  # e.g. "X-Cronwatch-Secret: abc123"

    def is_enabled(self) -> bool:
        return bool(self.url) and (self.on_failure or self.on_success)

    def __repr__(self) -> str:
        return (
            f"WebhookPolicy(url={self.url!r}, on_failure={self.on_failure}, "
            f"on_success={self.on_success}, timeout={self.timeout}s)"
        )


def get_webhook_policy(job: dict, config: dict) -> WebhookPolicy:
    """Resolve webhook policy for *job*, falling back to global config."""
    global_cfg = config.get("webhook", {})
    if isinstance(global_cfg, str):
        global_cfg = {"url": global_cfg}

    job_cfg = job.get("webhook", {})
    if isinstance(job_cfg, str):
        job_cfg = {"url": job_cfg}

    merged = {**global_cfg, **job_cfg}

    return WebhookPolicy(
        url=merged.get("url"),
        on_failure=bool(merged.get("on_failure", True)),
        on_success=bool(merged.get("on_success", False)),
        timeout=int(merged.get("timeout", 10)),
        secret_header=merged.get("secret_header"),
    )


def build_payload(result: JobResult) -> dict:
    """Build the JSON payload sent to the webhook endpoint."""
    return {
        "job": result.job_name,
        "success": result.success,
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "duration": result.duration,
        "started_at": result.started_at,
    }


def send_webhook(result: JobResult, policy: WebhookPolicy) -> bool:
    """POST the result payload to the configured webhook URL.

    Returns True on success, False on any network/HTTP error.
    """
    if not policy.is_enabled():
        return False
    if result.success and not policy.on_success:
        return False
    if not result.success and not policy.on_failure:
        return False

    payload = json.dumps(build_payload(result)).encode()
    req = urllib.request.Request(
        policy.url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    if policy.secret_header:
        key, _, value = policy.secret_header.partition(":")
        req.add_header(key.strip(), value.strip())

    try:
        with urllib.request.urlopen(req, timeout=policy.timeout) as resp:
            return resp.status < 400
    except (urllib.error.URLError, OSError):
        return False

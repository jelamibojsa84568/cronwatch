"""Output capture policy: control stdout/stderr retention for job runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


_DEFAULT_MAX_BYTES = 10_240  # 10 KB
_DEFAULT_CAPTURE_STDOUT = True
_DEFAULT_CAPTURE_STDERR = True


@dataclass
class CapturePolicy:
    capture_stdout: bool = _DEFAULT_CAPTURE_STDOUT
    capture_stderr: bool = _DEFAULT_CAPTURE_STDERR
    max_bytes: int = _DEFAULT_MAX_BYTES
    include_in_alerts: bool = True

    def is_capturing(self) -> bool:
        return self.capture_stdout or self.capture_stderr

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"CapturePolicy(stdout={self.capture_stdout}, "
            f"stderr={self.capture_stderr}, max_bytes={self.max_bytes}, "
            f"in_alerts={self.include_in_alerts})"
        )


def get_capture_policy(job: dict[str, Any], config: dict[str, Any]) -> CapturePolicy:
    """Build a CapturePolicy by merging global defaults with per-job overrides."""
    global_cfg: dict[str, Any] = config.get("output_capture", {})
    job_cfg: dict[str, Any] = job.get("output_capture", {})

    merged: dict[str, Any] = {**global_cfg, **job_cfg}

    return CapturePolicy(
        capture_stdout=bool(merged.get("capture_stdout", _DEFAULT_CAPTURE_STDOUT)),
        capture_stderr=bool(merged.get("capture_stderr", _DEFAULT_CAPTURE_STDERR)),
        max_bytes=int(merged.get("max_bytes", _DEFAULT_MAX_BYTES)),
        include_in_alerts=bool(merged.get("include_in_alerts", True)),
    )


def truncate_output(text: str, max_bytes: int) -> str:
    """Truncate *text* to at most *max_bytes* bytes (UTF-8), appending a notice."""
    if not text:
        return text
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    truncated = encoded[:max_bytes].decode("utf-8", errors="ignore")
    return truncated + "\n[... output truncated ...]"


def collect_output(policy: CapturePolicy, stdout: str, stderr: str) -> dict[str, str]:
    """Return a dict of captured streams according to *policy*."""
    result: dict[str, str] = {}
    if policy.capture_stdout:
        result["stdout"] = truncate_output(stdout or "", policy.max_bytes)
    if policy.capture_stderr:
        result["stderr"] = truncate_output(stderr or "", policy.max_bytes)
    return result

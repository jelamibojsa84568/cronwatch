"""Audit log: records every job execution event to a structured JSONL audit trail."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cronwatch.runner import JobResult


def _audit_path(log_dir: str, job_name: str) -> Path:
    """Return the audit log path for a given job."""
    safe = job_name.replace(" ", "_").replace("/", "_")
    return Path(log_dir) / "audit" / f"{safe}.audit.jsonl"


def record_audit_event(
    result: JobResult,
    log_dir: str,
    *,
    extra: dict[str, Any] | None = None,
) -> Path:
    """Append a single audit event for *result* and return the file path."""
    path = _audit_path(log_dir, result.job_name)
    path.parent.mkdir(parents=True, exist_ok=True)

    event: dict[str, Any] = {
        "job": result.job_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "exit_code": result.exit_code,
        "success": result.success,
        "duration": round(result.duration, 3),
        "command": result.command,
    }
    if extra:
        event.update(extra)

    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event) + "\n")

    return path


def read_audit_log(log_dir: str, job_name: str) -> list[dict[str, Any]]:
    """Return all audit events for *job_name*, oldest first."""
    path = _audit_path(log_dir, job_name)
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return events


def format_audit_text(events: list[dict[str, Any]]) -> str:
    """Render a human-readable audit summary."""
    if not events:
        return "No audit events found."
    lines = []
    for ev in events:
        status = "OK" if ev.get("success") else f"FAIL({ev.get('exit_code')})"
        lines.append(
            f"[{ev.get('timestamp', '?')}] {ev.get('job', '?')} "
            f"{status} duration={ev.get('duration', '?')}s"
        )
    return "\n".join(lines)

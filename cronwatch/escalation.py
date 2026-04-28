"""Alert escalation policy: re-notify after repeated failures."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


DEFAULT_THRESHOLD = 3       # failures before escalating
DEFAULT_INTERVAL = 3600     # seconds between escalation pings


def get_escalation_policy(job: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Return the effective escalation policy for *job*.

    Precedence: job-level > global > defaults.
    """
    global_esc = config.get("escalation", {})
    job_esc = job.get("escalation", {})

    if isinstance(global_esc, int):
        global_esc = {"threshold": global_esc}
    if isinstance(job_esc, int):
        job_esc = {"threshold": job_esc}

    merged: dict[str, Any] = {
        "threshold": DEFAULT_THRESHOLD,
        "interval": DEFAULT_INTERVAL,
        "enabled": True,
    }
    merged.update(global_esc)
    merged.update(job_esc)

    # coerce types
    merged["threshold"] = int(merged["threshold"])
    merged["interval"] = int(merged["interval"])
    merged["enabled"] = bool(merged["enabled"])
    return merged


def _state_path(state_dir: str | Path, job_name: str) -> Path:
    safe = job_name.replace("/", "_").replace(" ", "_")
    return Path(state_dir) / f"{safe}.escalation.json"


def _load_state(path: Path) -> dict[str, Any]:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"consecutive_failures": 0, "last_escalated": 0.0}


def _save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state))


def record_failure(state_dir: str | Path, job_name: str) -> int:
    """Increment consecutive failure count and return new count."""
    path = _state_path(state_dir, job_name)
    state = _load_state(path)
    state["consecutive_failures"] = state.get("consecutive_failures", 0) + 1
    _save_state(path, state)
    return state["consecutive_failures"]


def record_success(state_dir: str | Path, job_name: str) -> None:
    """Reset consecutive failure count on success."""
    path = _state_path(state_dir, job_name)
    state = _load_state(path)
    state["consecutive_failures"] = 0
    _save_state(path, state)


def should_escalate(
    state_dir: str | Path,
    job_name: str,
    policy: dict[str, Any],
) -> bool:
    """Return True if an escalation alert should be sent right now."""
    if not policy.get("enabled", True):
        return False
    path = _state_path(state_dir, job_name)
    state = _load_state(path)
    consecutive = state.get("consecutive_failures", 0)
    if consecutive < policy["threshold"]:
        return False
    elapsed = time.time() - state.get("last_escalated", 0.0)
    return elapsed >= policy["interval"]


def record_escalation_sent(state_dir: str | Path, job_name: str) -> None:
    """Stamp the last escalation time so the interval can be enforced."""
    path = _state_path(state_dir, job_name)
    state = _load_state(path)
    state["last_escalated"] = time.time()
    _save_state(path, state)

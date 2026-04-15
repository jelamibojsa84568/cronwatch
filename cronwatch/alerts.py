"""Alert throttling and dispatch logic for cronwatch."""

import json
import time
from pathlib import Path
from typing import Optional

DEFAULT_THROTTLE_SECONDS = 3600  # 1 hour


def _state_path(state_dir: str) -> Path:
    return Path(state_dir) / "alert_state.json"


def _load_state(state_dir: str) -> dict:
    path = _state_path(state_dir)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save_state(state_dir: str, state: dict) -> None:
    path = _state_path(state_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2))


def is_throttled(job_name: str, state_dir: str, throttle_seconds: int = DEFAULT_THROTTLE_SECONDS) -> bool:
    """Return True if an alert for job_name was sent within the throttle window."""
    state = _load_state(state_dir)
    last_sent: Optional[float] = state.get(job_name)
    if last_sent is None:
        return False
    return (time.time() - last_sent) < throttle_seconds


def record_alert_sent(job_name: str, state_dir: str) -> None:
    """Record the current timestamp as the last alert time for job_name."""
    state = _load_state(state_dir)
    state[job_name] = time.time()
    _save_state(state_dir, state)


def clear_alert_state(job_name: str, state_dir: str) -> None:
    """Remove throttle state for a job (e.g. after it recovers)."""
    state = _load_state(state_dir)
    state.pop(job_name, None)
    _save_state(state_dir, state)


def maybe_send_alert(job_name: str, send_fn, state_dir: str,
                     throttle_seconds: int = DEFAULT_THROTTLE_SECONDS) -> bool:
    """Call send_fn() only if not throttled. Returns True if alert was sent."""
    if is_throttled(job_name, state_dir, throttle_seconds):
        return False
    send_fn()
    record_alert_sent(job_name, state_dir)
    return True

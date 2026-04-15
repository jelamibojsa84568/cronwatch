"""Job execution history storage and retrieval using a simple JSON-based store."""

import json
import os
from datetime import datetime
from typing import List, Optional

DEFAULT_HISTORY_FILE = "/var/log/cronwatch/history.json"
MAX_HISTORY_ENTRIES = 500


def _load_raw(history_file: str) -> List[dict]:
    """Load raw history entries from disk."""
    if not os.path.exists(history_file):
        return []
    try:
        with open(history_file, "r") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def record_result(result, history_file: str = DEFAULT_HISTORY_FILE) -> None:
    """Append a JobResult to the history file, pruning old entries if needed."""
    entries = _load_raw(history_file)
    entry = {
        "job_name": result.job_name,
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "duration": result.duration,
        "timestamp": datetime.utcnow().isoformat(),
        "success": result.success,
    }
    entries.append(entry)
    if len(entries) > MAX_HISTORY_ENTRIES:
        entries = entries[-MAX_HISTORY_ENTRIES:]
    os.makedirs(os.path.dirname(history_file), exist_ok=True)
    with open(history_file, "w") as f:
        json.dump(entries, f, indent=2)


def get_history(
    job_name: Optional[str] = None,
    limit: int = 20,
    history_file: str = DEFAULT_HISTORY_FILE,
) -> List[dict]:
    """Return recent history entries, optionally filtered by job name."""
    entries = _load_raw(history_file)
    if job_name is not None:
        entries = [e for e in entries if e.get("job_name") == job_name]
    return entries[-limit:]


def last_failed(
    job_name: str, history_file: str = DEFAULT_HISTORY_FILE
) -> Optional[dict]:
    """Return the most recent failed entry for a given job, or None."""
    entries = get_history(job_name=job_name, limit=MAX_HISTORY_ENTRIES,
                         history_file=history_file)
    for entry in reversed(entries):
        if not entry.get("success", True):
            return entry
    return None

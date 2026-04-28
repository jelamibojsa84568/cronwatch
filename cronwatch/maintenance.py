"""Maintenance window support: suppress alerts during scheduled downtime."""

from __future__ import annotations

import re
from datetime import datetime, time
from typing import Any


class MaintenanceWindow:
    """Represents a single maintenance window for a job or globally."""

    def __init__(self, start: time, end: time, days: list[int] | None = None):
        self.start = start
        self.end = end
        # days: list of weekday ints (0=Mon … 6=Sun); None means every day
        self.days = days

    def is_active(self, now: datetime | None = None) -> bool:
        now = now or datetime.now()
        if self.days is not None and now.weekday() not in self.days:
            return False
        current = now.time().replace(second=0, microsecond=0)
        if self.start <= self.end:
            return self.start <= current <= self.end
        # overnight window e.g. 23:00 – 01:00
        return current >= self.start or current <= self.end

    def __repr__(self) -> str:
        days_str = str(self.days) if self.days is not None else "*"
        return f"<MaintenanceWindow {self.start}-{self.end} days={days_str}>"


_TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})$")
_DAY_NAMES = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


def _parse_time(value: str) -> time:
    m = _TIME_RE.match(value.strip())
    if not m:
        raise ValueError(f"Invalid time format {value!r}; expected HH:MM")
    return time(int(m.group(1)), int(m.group(2)))


def _parse_days(value: Any) -> list[int] | None:
    if value is None:
        return None
    if isinstance(value, list):
        items = value
    else:
        items = [v.strip() for v in str(value).split(",")]
    result = []
    for item in items:
        item = str(item).lower()
        if item in _DAY_NAMES:
            result.append(_DAY_NAMES[item])
        elif item.isdigit():
            result.append(int(item))
        else:
            raise ValueError(f"Unknown day {item!r}")
    return result or None


def parse_maintenance_windows(raw: Any) -> list[MaintenanceWindow]:
    """Parse maintenance window config from a job or global config dict."""
    if not raw:
        return []
    if isinstance(raw, dict):
        raw = [raw]
    windows = []
    for entry in raw:
        start = _parse_time(entry["start"])
        end = _parse_time(entry["end"])
        days = _parse_days(entry.get("days"))
        windows.append(MaintenanceWindow(start, end, days))
    return windows


def is_in_maintenance(job: dict, config: dict, now: datetime | None = None) -> bool:
    """Return True if the job is currently inside any maintenance window."""
    global_raw = config.get("maintenance", [])
    job_raw = job.get("maintenance", [])
    windows = parse_maintenance_windows(global_raw) + parse_maintenance_windows(job_raw)
    return any(w.is_active(now) for w in windows)

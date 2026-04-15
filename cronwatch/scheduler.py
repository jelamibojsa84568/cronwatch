"""Scheduler module for cronwatch.

Parses job definitions from config and determines which jobs
are due to run based on their cron expressions.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Dict, Any

from croniter import croniter

logger = logging.getLogger(__name__)


def parse_jobs(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract and validate job definitions from config.

    Args:
        config: Parsed configuration dictionary.

    Returns:
        List of job dictionaries with at least 'name', 'schedule', and 'command'.

    Raises:
        ValueError: If a job is missing required fields or has an invalid schedule.
    """
    jobs = config.get("jobs", [])
    validated = []

    for job in jobs:
        name = job.get("name")
        schedule = job.get("schedule")
        command = job.get("command")

        if not name:
            raise ValueError(f"Job is missing required field 'name': {job}")
        if not schedule:
            raise ValueError(f"Job '{name}' is missing required field 'schedule'.")
        if not command:
            raise ValueError(f"Job '{name}' is missing required field 'command'.")

        if not croniter.is_valid(schedule):
            raise ValueError(
                f"Job '{name}' has an invalid cron expression: '{schedule}'."
            )

        validated.append(dict(job))

    return validated


def get_due_jobs(
    jobs: List[Dict[str, Any]],
    reference_time: datetime | None = None,
    tolerance_seconds: int = 60,
) -> List[Dict[str, Any]]:
    """Return jobs whose next scheduled run falls within *tolerance_seconds* of
    *reference_time* (defaults to now).

    Args:
        jobs: List of validated job dictionaries.
        reference_time: The moment to check against (UTC). Defaults to now.
        tolerance_seconds: Window (in seconds) around the reference time.

    Returns:
        Subset of *jobs* that are due.
    """
    if reference_time is None:
        reference_time = datetime.utcnow()

    due = []
    for job in jobs:
        cron = croniter(job["schedule"], reference_time)
        prev_run = cron.get_prev(datetime)
        delta = abs((reference_time - prev_run).total_seconds())
        if delta <= tolerance_seconds:
            logger.debug("Job '%s' is due (delta=%.1fs).", job["name"], delta)
            due.append(job)

    return due

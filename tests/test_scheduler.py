"""Tests for cronwatch.scheduler."""

from __future__ import annotations

from datetime import datetime

import pytest

from cronwatch.scheduler import get_due_jobs, parse_jobs


# ---------------------------------------------------------------------------
# parse_jobs
# ---------------------------------------------------------------------------

VALID_CONFIG = {
    "jobs": [
        {"name": "backup", "schedule": "0 2 * * *", "command": "/usr/bin/backup.sh"},
        {"name": "cleanup", "schedule": "30 3 * * 0", "command": "/usr/bin/cleanup.sh"},
    ]
}


def test_parse_jobs_returns_all_valid_jobs():
    jobs = parse_jobs(VALID_CONFIG)
    assert len(jobs) == 2
    assert jobs[0]["name"] == "backup"
    assert jobs[1]["name"] == "cleanup"


def test_parse_jobs_empty_list_when_no_jobs_key():
    jobs = parse_jobs({})
    assert jobs == []


def test_parse_jobs_raises_for_missing_name():
    config = {"jobs": [{"schedule": "* * * * *", "command": "echo hi"}]}
    with pytest.raises(ValueError, match="missing required field 'name'"):
        parse_jobs(config)


def test_parse_jobs_raises_for_missing_schedule():
    config = {"jobs": [{"name": "myjob", "command": "echo hi"}]}
    with pytest.raises(ValueError, match="missing required field 'schedule'"):
        parse_jobs(config)


def test_parse_jobs_raises_for_missing_command():
    config = {"jobs": [{"name": "myjob", "schedule": "* * * * *"}]}
    with pytest.raises(ValueError, match="missing required field 'command'"):
        parse_jobs(config)


def test_parse_jobs_raises_for_invalid_cron_expression():
    config = {
        "jobs": [{"name": "bad", "schedule": "not-a-cron", "command": "echo"}]
    }
    with pytest.raises(ValueError, match="invalid cron expression"):
        parse_jobs(config)


# ---------------------------------------------------------------------------
# get_due_jobs
# ---------------------------------------------------------------------------


def _make_jobs(*schedules: str) -> list:
    return [
        {"name": f"job_{i}", "schedule": s, "command": "true"}
        for i, s in enumerate(schedules)
    ]


def test_get_due_jobs_returns_job_matching_reference_time():
    # 2024-01-15 02:00 UTC — matches "0 2 * * *"
    ref = datetime(2024, 1, 15, 2, 0, 0)
    jobs = _make_jobs("0 2 * * *")
    due = get_due_jobs(jobs, reference_time=ref)
    assert len(due) == 1
    assert due[0]["name"] == "job_0"


def test_get_due_jobs_excludes_job_not_matching_reference_time():
    # 2024-01-15 03:00 UTC — does NOT match "0 2 * * *"
    ref = datetime(2024, 1, 15, 3, 0, 0)
    jobs = _make_jobs("0 2 * * *")
    due = get_due_jobs(jobs, reference_time=ref)
    assert due == []


def test_get_due_jobs_respects_tolerance():
    # 30s after the scheduled minute — within default 60s window
    ref = datetime(2024, 1, 15, 2, 0, 30)
    jobs = _make_jobs("0 2 * * *")
    due = get_due_jobs(jobs, reference_time=ref, tolerance_seconds=60)
    assert len(due) == 1


def test_get_due_jobs_outside_tolerance_excluded():
    # 90s after the scheduled minute — outside 60s window
    ref = datetime(2024, 1, 15, 2, 1, 30)
    jobs = _make_jobs("0 2 * * *")
    due = get_due_jobs(jobs, reference_time=ref, tolerance_seconds=60)
    assert due == []


def test_get_due_jobs_empty_list_returns_empty():
    ref = datetime(2024, 1, 15, 2, 0, 0)
    assert get_due_jobs([], reference_time=ref) == []

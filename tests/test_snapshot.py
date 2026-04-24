"""Tests for cronwatch.snapshot."""

import json
import os
import time

import pytest

from cronwatch.snapshot import (
    _job_fingerprint,
    capture_snapshot,
    diff_snapshots,
    format_diff_text,
    load_snapshot,
)


@pytest.fixture()
def log_dir(tmp_path):
    return str(tmp_path)


JOBS = [
    {"name": "backup", "schedule": "0 2 * * *", "command": "/usr/bin/backup.sh"},
    {"name": "cleanup", "schedule": "0 3 * * *", "command": "/usr/bin/cleanup.sh"},
]


def test_job_fingerprint_is_stable():
    job = {"name": "backup", "schedule": "0 2 * * *", "command": "/usr/bin/backup.sh"}
    assert _job_fingerprint(job) == _job_fingerprint(job)


def test_job_fingerprint_differs_on_change():
    job1 = {"name": "backup", "schedule": "0 2 * * *", "command": "/usr/bin/backup.sh"}
    job2 = {"name": "backup", "schedule": "0 4 * * *", "command": "/usr/bin/backup.sh"}
    assert _job_fingerprint(job1) != _job_fingerprint(job2)


def test_capture_snapshot_creates_file(log_dir):
    capture_snapshot(JOBS, log_dir)
    snap_path = os.path.join(log_dir, "snapshots", "job_snapshot.json")
    assert os.path.exists(snap_path)


def test_capture_snapshot_contains_all_jobs(log_dir):
    snap = capture_snapshot(JOBS, log_dir)
    assert "backup" in snap["jobs"]
    assert "cleanup" in snap["jobs"]


def test_capture_snapshot_has_captured_at(log_dir):
    before = time.time()
    snap = capture_snapshot(JOBS, log_dir)
    assert snap["captured_at"] >= before


def test_load_snapshot_returns_none_when_missing(log_dir):
    assert load_snapshot(log_dir) is None


def test_load_snapshot_returns_saved_data(log_dir):
    capture_snapshot(JOBS, log_dir)
    snap = load_snapshot(log_dir)
    assert snap is not None
    assert "backup" in snap["jobs"]


def test_diff_snapshots_detects_added():
    old = {"jobs": {"backup": {"fingerprint": "abc"}}}
    new = {"jobs": {"backup": {"fingerprint": "abc"}, "cleanup": {"fingerprint": "xyz"}}}
    diff = diff_snapshots(old, new)
    assert "cleanup" in diff["added"]
    assert diff["removed"] == []
    assert diff["changed"] == []


def test_diff_snapshots_detects_removed():
    old = {"jobs": {"backup": {"fingerprint": "abc"}, "cleanup": {"fingerprint": "xyz"}}}
    new = {"jobs": {"backup": {"fingerprint": "abc"}}}
    diff = diff_snapshots(old, new)
    assert "cleanup" in diff["removed"]


def test_diff_snapshots_detects_changed():
    old = {"jobs": {"backup": {"fingerprint": "abc"}}}
    new = {"jobs": {"backup": {"fingerprint": "def"}}}
    diff = diff_snapshots(old, new)
    assert "backup" in diff["changed"]


def test_format_diff_text_no_changes():
    diff = {"added": [], "removed": [], "changed": []}
    assert format_diff_text(diff) == "No changes detected."


def test_format_diff_text_with_changes():
    diff = {"added": ["newjob"], "removed": ["oldjob"], "changed": []}
    text = format_diff_text(diff)
    assert "Added" in text
    assert "newjob" in text
    assert "Removed" in text
    assert "oldjob" in text

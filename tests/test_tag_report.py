"""Tests for cronwatch.tag_report module."""
import json
import os
import pytest
from cronwatch.tag_report import build_tag_report, format_tag_report


JOBS = [
    {"name": "backup", "schedule": "0 2 * * *", "command": "b.sh", "tags": ["nightly", "critical"]},
    {"name": "cleanup", "schedule": "0 3 * * *", "command": "c.sh", "tags": ["nightly"]},
    {"name": "report", "schedule": "0 8 * * 1", "command": "r.sh", "tags": ["weekly"]},
]


def _write_history(history_dir, job_name, entries):
    path = os.path.join(history_dir, f"{job_name}.jsonl")
    with open(path, "w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")


@pytest.fixture
def history_dir(tmp_path):
    return str(tmp_path)


def test_build_tag_report_counts_runs(history_dir):
    _write_history(history_dir, "backup", [{"success": True}, {"success": True}])
    _write_history(history_dir, "cleanup", [{"success": True}])
    _write_history(history_dir, "report", [])
    summary = build_tag_report(JOBS, history_dir=history_dir)
    assert summary["nightly"]["runs"] == 3


def test_build_tag_report_counts_failures(history_dir):
    _write_history(history_dir, "backup", [{"success": False}, {"success": True}])
    _write_history(history_dir, "cleanup", [{"success": False}])
    _write_history(history_dir, "report", [])
    summary = build_tag_report(JOBS, history_dir=history_dir)
    assert summary["nightly"]["failures"] == 2
    assert summary["critical"]["failures"] == 1


def test_build_tag_report_zero_for_empty_history(history_dir):
    summary = build_tag_report(JOBS, history_dir=history_dir)
    assert summary["weekly"]["runs"] == 0
    assert summary["weekly"]["failures"] == 0


def test_format_tag_report_contains_tag_names(history_dir):
    summary = build_tag_report(JOBS, history_dir=history_dir)
    text = format_tag_report(summary)
    assert "nightly" in text
    assert "weekly" in text
    assert "critical" in text


def test_format_tag_report_empty_summary():
    text = format_tag_report({})
    assert "No tagged jobs" in text


def test_format_tag_report_shows_percentage(history_dir):
    _write_history(history_dir, "backup", [{"success": False}, {"success": False}])
    _write_history(history_dir, "cleanup", [])
    _write_history(history_dir, "report", [])
    summary = build_tag_report(JOBS, history_dir=history_dir)
    text = format_tag_report(summary)
    assert "100.0%" in text

"""Tests for cronwatch.report module."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from cronwatch.report import _parse_window, build_report, format_report_text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_entry(history_dir: Path, job_name: str, entry: dict) -> None:
    job_file = history_dir / f"{job_name}.jsonl"
    with job_file.open("a") as fh:
        fh.write(json.dumps(entry) + "\n")


def _ts(offset_hours: float = 0) -> str:
    return (datetime.utcnow() - timedelta(hours=offset_hours)).isoformat()


@pytest.fixture
def history_dir(tmp_path):
    return tmp_path


# ---------------------------------------------------------------------------
# _parse_window
# ---------------------------------------------------------------------------

def test_parse_window_hours():
    assert _parse_window("6h") == timedelta(hours=6)


def test_parse_window_days():
    assert _parse_window("7d") == timedelta(days=7)


def test_parse_window_invalid_unit():
    with pytest.raises(ValueError, match="Unknown time unit"):
        _parse_window("5m")


def test_parse_window_invalid_format():
    with pytest.raises(ValueError, match="Invalid window format"):
        _parse_window("abch")


# ---------------------------------------------------------------------------
# build_report
# ---------------------------------------------------------------------------

def test_build_report_counts_runs(history_dir):
    job = {"name": "backup"}
    for _ in range(3):
        _write_entry(history_dir, "backup", {"timestamp": _ts(1), "success": True, "exit_code": 0})
    report = build_report([job], str(history_dir), window="24h")
    assert report["total_runs"] == 3


def test_build_report_counts_failures(history_dir):
    job = {"name": "sync"}
    _write_entry(history_dir, "sync", {"timestamp": _ts(1), "success": True, "exit_code": 0})
    _write_entry(history_dir, "sync", {"timestamp": _ts(2), "success": False, "exit_code": 1})
    report = build_report([job], str(history_dir), window="24h")
    assert report["total_failures"] == 1


def test_build_report_excludes_old_entries(history_dir):
    job = {"name": "cleanup"}
    _write_entry(history_dir, "cleanup", {"timestamp": _ts(0.5), "success": True, "exit_code": 0})
    _write_entry(history_dir, "cleanup", {"timestamp": _ts(25), "success": False, "exit_code": 1})
    report = build_report([job], str(history_dir), window="24h")
    assert report["total_runs"] == 1
    assert report["total_failures"] == 0


def test_build_report_success_rate(history_dir):
    job = {"name": "deploy"}
    _write_entry(history_dir, "deploy", {"timestamp": _ts(1), "success": True, "exit_code": 0})
    _write_entry(history_dir, "deploy", {"timestamp": _ts(2), "success": True, "exit_code": 0})
    _write_entry(history_dir, "deploy", {"timestamp": _ts(3), "success": False, "exit_code": 2})
    report = build_report([job], str(history_dir), window="24h")
    assert report["jobs"][0]["success_rate"] == pytest.approx(66.7)


def test_build_report_no_runs_gives_none_rate(history_dir):
    job = {"name": "idle"}
    report = build_report([job], str(history_dir), window="24h")
    assert report["jobs"][0]["success_rate"] is None
    assert report["jobs"][0]["last_run"] is None


# ---------------------------------------------------------------------------
# format_report_text
# ---------------------------------------------------------------------------

def test_format_report_text_contains_window(history_dir):
    report = build_report([], str(history_dir), window="12h")
    text = format_report_text(report)
    assert "12h" in text


def test_format_report_text_contains_job_name(history_dir):
    job = {"name": "my-job"}
    _write_entry(history_dir, "my-job", {"timestamp": _ts(1), "success": True, "exit_code": 0})
    report = build_report([job], str(history_dir), window="24h")
    text = format_report_text(report)
    assert "my-job" in text

"""Tests for cronwatch.digest report builder."""

import json
import time
from pathlib import Path

import pytest

from cronwatch.digest import build_digest, format_digest_text, _format_duration


@pytest.fixture
def history_dir(tmp_path):
    return str(tmp_path / "history")


def _write_entries(history_dir, job_name, entries):
    path = Path(history_dir) / f"{job_name}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")


def _entry(success=True, exit_code=0, duration=5.0, offset_seconds=0):
    return {
        "success": success,
        "exit_code": exit_code,
        "duration": duration,
        "timestamp": time.time() - offset_seconds,
    }


def test_format_duration_seconds():
    assert _format_duration(45.0) == "45.0s"


def test_format_duration_minutes():
    assert _format_duration(125.0) == "2m 5s"


def test_build_digest_empty_history(history_dir):
    report = build_digest(["backup"], history_dir)
    assert report["backup"]["total_runs"] == 0
    assert report["backup"]["success_rate"] is None


def test_build_digest_counts_runs(history_dir):
    _write_entries(history_dir, "backup", [_entry(), _entry(), _entry()])
    report = build_digest(["backup"], history_dir)
    assert report["backup"]["total_runs"] == 3


def test_build_digest_counts_failures(history_dir):
    _write_entries(history_dir, "backup", [
        _entry(success=True),
        _entry(success=False, exit_code=1),
        _entry(success=False, exit_code=2),
    ])
    report = build_digest(["backup"], history_dir)
    assert report["backup"]["failures"] == 2


def test_build_digest_success_rate(history_dir):
    _write_entries(history_dir, "backup", [
        _entry(success=True),
        _entry(success=True),
        _entry(success=False, exit_code=1),
        _entry(success=False, exit_code=1),
    ])
    report = build_digest(["backup"], history_dir)
    assert report["backup"]["success_rate"] == 50.0


def test_build_digest_excludes_old_entries(history_dir):
    _write_entries(history_dir, "backup", [
        _entry(offset_seconds=90000),  # older than 24h
        _entry(),
    ])
    report = build_digest(["backup"], history_dir, since_hours=24)
    assert report["backup"]["total_runs"] == 1


def test_build_digest_avg_duration(history_dir):
    _write_entries(history_dir, "backup", [
        _entry(duration=10.0),
        _entry(duration=20.0),
    ])
    report = build_digest(["backup"], history_dir)
    assert report["backup"]["avg_duration"] == "15.0s"


def test_format_digest_text_contains_job_name(history_dir):
    report = build_digest(["nightly-sync"], history_dir)
    text = format_digest_text(report)
    assert "nightly-sync" in text


def test_format_digest_text_shows_header(history_dir):
    report = build_digest(["job"], history_dir)
    text = format_digest_text(report, since_hours=12)
    assert "last 12h" in text

"""Tests for cronwatch.history module."""

import json
import os
import pytest
from unittest.mock import MagicMock

from cronwatch.history import (
    record_result,
    get_history,
    last_failed,
    MAX_HISTORY_ENTRIES,
)


def _make_result(job_name="test-job", exit_code=0, stdout="ok", stderr="", duration=1.2):
    result = MagicMock()
    result.job_name = job_name
    result.exit_code = exit_code
    result.stdout = stdout
    result.stderr = stderr
    result.duration = duration
    result.success = exit_code == 0
    return result


def test_record_result_creates_file(tmp_path):
    hfile = str(tmp_path / "history.json")
    record_result(_make_result(), history_file=hfile)
    assert os.path.exists(hfile)


def test_record_result_stores_fields(tmp_path):
    hfile = str(tmp_path / "history.json")
    record_result(_make_result(job_name="backup", exit_code=0), history_file=hfile)
    with open(hfile) as f:
        data = json.load(f)
    assert len(data) == 1
    assert data[0]["job_name"] == "backup"
    assert data[0]["exit_code"] == 0
    assert data[0]["success"] is True
    assert "timestamp" in data[0]


def test_record_result_appends_entries(tmp_path):
    hfile = str(tmp_path / "history.json")
    record_result(_make_result(job_name="job-a"), history_file=hfile)
    record_result(_make_result(job_name="job-b"), history_file=hfile)
    entries = get_history(history_file=hfile, limit=10)
    assert len(entries) == 2


def test_record_result_prunes_old_entries(tmp_path):
    hfile = str(tmp_path / "history.json")
    for i in range(MAX_HISTORY_ENTRIES + 10):
        record_result(_make_result(job_name=f"job-{i}"), history_file=hfile)
    with open(hfile) as f:
        data = json.load(f)
    assert len(data) == MAX_HISTORY_ENTRIES


def test_get_history_filters_by_job_name(tmp_path):
    hfile = str(tmp_path / "history.json")
    record_result(_make_result(job_name="alpha"), history_file=hfile)
    record_result(_make_result(job_name="beta"), history_file=hfile)
    record_result(_make_result(job_name="alpha"), history_file=hfile)
    results = get_history(job_name="alpha", history_file=hfile)
    assert all(r["job_name"] == "alpha" for r in results)
    assert len(results) == 2


def test_get_history_returns_empty_when_no_file(tmp_path):
    hfile = str(tmp_path / "nonexistent.json")
    assert get_history(history_file=hfile) == []


def test_last_failed_returns_most_recent_failure(tmp_path):
    hfile = str(tmp_path / "history.json")
    record_result(_make_result(exit_code=1, stderr="error"), history_file=hfile)
    record_result(_make_result(exit_code=0), history_file=hfile)
    record_result(_make_result(exit_code=2, stderr="fatal"), history_file=hfile)
    entry = last_failed("test-job", history_file=hfile)
    assert entry is not None
    assert entry["exit_code"] == 2


def test_last_failed_returns_none_when_all_passed(tmp_path):
    hfile = str(tmp_path / "history.json")
    record_result(_make_result(exit_code=0), history_file=hfile)
    assert last_failed("test-job", history_file=hfile) is None

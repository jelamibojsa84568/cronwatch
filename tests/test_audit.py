"""Tests for cronwatch.audit and cronwatch.cli_audit."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from cronwatch.audit import (
    _audit_path,
    format_audit_text,
    record_audit_event,
    read_audit_log,
)
from cronwatch.cli_audit import audit
from cronwatch.runner import JobResult


def _make_result(
    name: str = "backup",
    exit_code: int = 0,
    duration: float = 1.5,
    command: str = "echo hi",
) -> JobResult:
    return JobResult(
        job_name=name,
        command=command,
        exit_code=exit_code,
        stdout="",
        stderr="",
        duration=duration,
    )


@pytest.fixture()
def log_dir(tmp_path: Path) -> str:
    return str(tmp_path)


def test_record_audit_event_creates_file(log_dir: str) -> None:
    result = _make_result()
    path = record_audit_event(result, log_dir)
    assert path.exists()


def test_record_audit_event_contains_fields(log_dir: str) -> None:
    result = _make_result(exit_code=0)
    record_audit_event(result, log_dir)
    events = read_audit_log(log_dir, "backup")
    assert len(events) == 1
    ev = events[0]
    assert ev["job"] == "backup"
    assert ev["exit_code"] == 0
    assert ev["success"] is True
    assert ev["duration"] == 1.5


def test_record_audit_event_appends(log_dir: str) -> None:
    r1 = _make_result(exit_code=0)
    r2 = _make_result(exit_code=1)
    record_audit_event(r1, log_dir)
    record_audit_event(r2, log_dir)
    events = read_audit_log(log_dir, "backup")
    assert len(events) == 2


def test_record_audit_event_extra_fields(log_dir: str) -> None:
    result = _make_result()
    record_audit_event(result, log_dir, extra={"server": "prod-1"})
    events = read_audit_log(log_dir, "backup")
    assert events[0]["server"] == "prod-1"


def test_read_audit_log_empty_when_no_file(log_dir: str) -> None:
    assert read_audit_log(log_dir, "nonexistent") == []


def test_format_audit_text_no_events() -> None:
    assert "No audit" in format_audit_text([])


def test_format_audit_text_shows_status(log_dir: str) -> None:
    record_audit_event(_make_result(exit_code=0), log_dir)
    record_audit_event(_make_result(exit_code=2), log_dir)
    events = read_audit_log(log_dir, "backup")
    text = format_audit_text(events)
    assert "OK" in text
    assert "FAIL(2)" in text


def test_audit_path_sanitizes_name(tmp_path: Path) -> None:
    p = _audit_path(str(tmp_path), "my job/name")
    assert " " not in p.name
    assert "/" not in p.name


# --- CLI tests ---


def test_cmd_show_audit(log_dir: str) -> None:
    record_audit_event(_make_result(), log_dir)
    runner = CliRunner()
    result = runner.invoke(audit, ["show", "backup", "--config", ""], catch_exceptions=False,
                           env={"CRONWATCH_LOG_DIR": log_dir})
    # Invoke directly with patched config
    from unittest.mock import patch
    with patch("cronwatch.cli_audit.load_config", return_value={"log_dir": log_dir}):
        result = runner.invoke(audit, ["show", "backup"])
    assert result.exit_code == 0
    assert "backup" in result.output


def test_cmd_audit_count(log_dir: str) -> None:
    record_audit_event(_make_result(exit_code=0), log_dir)
    record_audit_event(_make_result(exit_code=1), log_dir)
    from unittest.mock import patch
    runner = CliRunner()
    with patch("cronwatch.cli_audit.load_config", return_value={"log_dir": log_dir}):
        result = runner.invoke(audit, ["count", "backup"])
    assert result.exit_code == 0
    assert result.output.strip() == "2"


def test_cmd_audit_count_failures_only(log_dir: str) -> None:
    record_audit_event(_make_result(exit_code=0), log_dir)
    record_audit_event(_make_result(exit_code=1), log_dir)
    from unittest.mock import patch
    runner = CliRunner()
    with patch("cronwatch.cli_audit.load_config", return_value={"log_dir": log_dir}):
        result = runner.invoke(audit, ["count", "backup", "--failures-only"])
    assert result.output.strip() == "1"

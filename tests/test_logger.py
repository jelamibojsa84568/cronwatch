"""Tests for cronwatch.logger module."""

import logging
import os
from pathlib import Path

import pytest

from cronwatch.logger import get_log_path, log_job_result, setup_job_logger


def test_get_log_path_basic():
    path = get_log_path("/var/log/cronwatch", "backup_db")
    assert path == Path("/var/log/cronwatch/backup_db.log")


def test_get_log_path_sanitizes_spaces_and_slashes():
    path = get_log_path("/logs", "my job/name here")
    assert " " not in str(path)
    assert path.name == "my_job-name_here.log"


def test_setup_job_logger_creates_log_dir(tmp_path):
    log_dir = str(tmp_path / "new_logs")
    logger = setup_job_logger("test_job", log_dir)
    assert os.path.isdir(log_dir)


def test_setup_job_logger_returns_logger_instance(tmp_path):
    logger = setup_job_logger("my_cron", str(tmp_path))
    assert isinstance(logger, logging.Logger)
    assert logger.name == "cronwatch.job.my_cron"


def test_setup_job_logger_no_duplicate_handlers(tmp_path):
    logger1 = setup_job_logger("dedup_job", str(tmp_path))
    handler_count_first = len(logger1.handlers)
    logger2 = setup_job_logger("dedup_job", str(tmp_path))
    assert len(logger2.handlers) == handler_count_first


def test_log_job_result_creates_log_file(tmp_path):
    log_job_result(
        job_name="nightly_sync",
        exit_code=0,
        duration=1.234,
        stdout="done",
        stderr="",
        log_dir=str(tmp_path),
    )
    log_file = tmp_path / "nightly_sync.log"
    assert log_file.exists()


def test_log_job_result_success_contains_expected_fields(tmp_path):
    log_job_result(
        job_name="check_disk",
        exit_code=0,
        duration=0.05,
        stdout="ok",
        stderr="",
        log_dir=str(tmp_path),
    )
    content = (tmp_path / "check_disk.log").read_text()
    assert "SUCCESS" in content
    assert "exit_code=0" in content
    assert "duration=0.050s" in content


def test_log_job_result_failure_contains_failure_status(tmp_path):
    log_job_result(
        job_name="broken_job",
        exit_code=1,
        duration=2.0,
        stdout="",
        stderr="something went wrong",
        log_dir=str(tmp_path),
    )
    content = (tmp_path / "broken_job.log").read_text()
    assert "FAILURE" in content
    assert "exit_code=1" in content

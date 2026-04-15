"""Tests for cronwatch.runner."""

import sys
import pytest
from unittest.mock import patch

from cronwatch.runner import JobResult, run_job


# ---------------------------------------------------------------------------
# JobResult
# ---------------------------------------------------------------------------

def test_job_result_success_property_true_on_zero_exit():
    result = JobResult(
        job_name="backup", command="true",
        exit_code=0, stdout="", stderr="",
        duration_seconds=0.1,
    )
    assert result.success is True


def test_job_result_success_property_false_on_nonzero_exit():
    result = JobResult(
        job_name="backup", command="false",
        exit_code=1, stdout="", stderr="error",
        duration_seconds=0.1,
    )
    assert result.success is False


def test_job_result_repr_contains_job_name():
    result = JobResult(
        job_name="my-job", command="echo hi",
        exit_code=0, stdout="hi", stderr="",
        duration_seconds=0.05,
    )
    assert "my-job" in repr(result)
    assert "OK" in repr(result)


def test_job_result_repr_shows_failed_exit_code():
    result = JobResult(
        job_name="bad-job", command="exit 2",
        exit_code=2, stdout="", stderr="",
        duration_seconds=0.02,
    )
    assert "FAILED" in repr(result)
    assert "exit=2" in repr(result)


# ---------------------------------------------------------------------------
# run_job
# ---------------------------------------------------------------------------

def test_run_job_successful_command():
    result = run_job("echo-job", "echo hello")
    assert result.success
    assert result.exit_code == 0
    assert result.stdout == "hello"
    assert result.job_name == "echo-job"
    assert result.duration_seconds >= 0


def test_run_job_failing_command():
    result = run_job("fail-job", "exit 42", shell=True)
    assert not result.success
    assert result.exit_code == 42


def test_run_job_captures_stderr():
    result = run_job("err-job", "echo oops >&2", shell=True)
    assert "oops" in result.stderr


def test_run_job_timeout_sets_exit_code_minus_one():
    result = run_job("slow-job", "sleep 10", timeout=1)
    assert result.exit_code == -1
    assert "timed out" in result.stderr.lower()


def test_run_job_duration_is_positive():
    result = run_job("timing-job", "echo ok")
    assert result.duration_seconds > 0


def test_run_job_stores_command():
    cmd = "echo stored"
    result = run_job("store-test", cmd)
    assert result.command == cmd

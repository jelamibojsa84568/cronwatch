"""Tests for cronwatch.cli_retry."""
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cronwatch.cli_retry import cmd_retry_run
from cronwatch.runner import JobResult
from cronwatch.retry import RetryOutcome


def _result(name, exit_code):
    return JobResult(job_name=name, command="echo hi", exit_code=exit_code,
                     stdout="", stderr="", duration=0.1)


CONFIG = {
    "log_dir": "/tmp/cw_test_retry",
    "jobs": [{"name": "backup", "command": "echo backup", "schedule": "0 * * * *"}],
}


@patch("cronwatch.cli_retry.record_result")
@patch("cronwatch.cli_retry.log_job_result")
@patch("cronwatch.cli_retry.setup_job_logger", return_value=MagicMock())
@patch("cronwatch.cli_retry.run_with_retry")
@patch("cronwatch.cli_retry.load_config", return_value=CONFIG)
def test_cmd_retry_run_success(lc, rwr, sjl, ljr, rr):
    rwr.return_value = RetryOutcome(
        job_name="backup", attempts=1,
        final_result=_result("backup", 0), succeeded=True
    )
    runner = CliRunner()
    result = runner.invoke(cmd_retry_run, ["backup"])
    assert result.exit_code == 0
    assert "succeeded" in result.output


@patch("cronwatch.cli_retry.record_result")
@patch("cronwatch.cli_retry.log_job_result")
@patch("cronwatch.cli_retry.setup_job_logger", return_value=MagicMock())
@patch("cronwatch.cli_retry.run_with_retry")
@patch("cronwatch.cli_retry.load_config", return_value=CONFIG)
def test_cmd_retry_run_failure_exits_1(lc, rwr, sjl, ljr, rr):
    rwr.return_value = RetryOutcome(
        job_name="backup", attempts=3,
        final_result=_result("backup", 1), succeeded=False
    )
    runner = CliRunner()
    result = runner.invoke(cmd_retry_run, ["backup"])
    assert result.exit_code == 1


@patch("cronwatch.cli_retry.load_config", return_value=CONFIG)
def test_cmd_retry_run_unknown_job(lc):
    runner = CliRunner()
    result = runner.invoke(cmd_retry_run, ["nonexistent"])
    assert result.exit_code != 0
    assert "not found" in result.output


@patch("cronwatch.cli_retry.record_result")
@patch("cronwatch.cli_retry.log_job_result")
@patch("cronwatch.cli_retry.setup_job_logger", return_value=MagicMock())
@patch("cronwatch.cli_retry.run_with_retry")
@patch("cronwatch.cli_retry.load_config", return_value=CONFIG)
def test_cmd_retry_run_passes_overrides(lc, rwr, sjl, ljr, rr):
    rwr.return_value = RetryOutcome(
        job_name="backup", attempts=1,
        final_result=_result("backup", 0), succeeded=True
    )
    runner = CliRunner()
    runner.invoke(cmd_retry_run, ["backup", "--max-attempts", "5", "--delay", "2.0"])
    _, kwargs = rwr.call_args
    policy = rwr.call_args[0][1]
    assert policy.max_attempts == 5
    assert policy.delay_seconds == 2.0

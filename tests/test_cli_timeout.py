"""Tests for cronwatch/cli_timeout.py — timeout command group."""

import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from cronwatch.cli_timeout import timeout, cmd_timeout_run
from cronwatch.runner import JobResult
from cronwatch.timeout import JobTimeoutError, TimeoutPolicy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _result(name="backup", exit_code=0, stdout="ok", stderr="", duration=1.2):
    """Build a minimal JobResult for use in tests."""
    return JobResult(
        job_name=name,
        command="/usr/bin/backup",
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        duration=duration,
        timed_out=False,
    )


@pytest.fixture()
def runner():
    return CliRunner()


@pytest.fixture()
def base_config():
    return {
        "jobs": [
            {
                "name": "backup",
                "command": "/usr/bin/backup",
                "schedule": "0 2 * * *",
                "timeout": 30,
            }
        ],
        "timeout": {"default": 60},
    }


# ---------------------------------------------------------------------------
# cmd_timeout_run — success path
# ---------------------------------------------------------------------------

def test_cmd_timeout_run_success(runner, base_config):
    """A job that completes within its timeout exits with code 0."""
    ok = _result("backup", exit_code=0)

    with patch("cronwatch.cli_timeout.load_config", return_value=base_config), \
         patch("cronwatch.cli_timeout.parse_jobs", return_value=base_config["jobs"]), \
         patch("cronwatch.cli_timeout.get_timeout_policy",
               return_value=TimeoutPolicy(seconds=30)), \
         patch("cronwatch.cli_timeout.run_job_with_timeout", return_value=ok):

        result = runner.invoke(cmd_timeout_run, ["backup"])

    assert result.exit_code == 0
    assert "backup" in result.output


def test_cmd_timeout_run_failure_exits_1(runner, base_config):
    """A job that exits non-zero causes the CLI to exit with code 1."""
    fail = _result("backup", exit_code=1, stderr="something went wrong")

    with patch("cronwatch.cli_timeout.load_config", return_value=base_config), \
         patch("cronwatch.cli_timeout.parse_jobs", return_value=base_config["jobs"]), \
         patch("cronwatch.cli_timeout.get_timeout_policy",
               return_value=TimeoutPolicy(seconds=30)), \
         patch("cronwatch.cli_timeout.run_job_with_timeout", return_value=fail):

        result = runner.invoke(cmd_timeout_run, ["backup"])

    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# cmd_timeout_run — timeout path
# ---------------------------------------------------------------------------

def test_cmd_timeout_run_reports_timeout(runner, base_config):
    """When a job times out, the output mentions the timeout and CLI exits 1."""
    timed_out = _result("backup", exit_code=1)
    timed_out = JobResult(
        job_name="backup",
        command="/usr/bin/backup",
        exit_code=1,
        stdout="",
        stderr="",
        duration=30.1,
        timed_out=True,
    )

    with patch("cronwatch.cli_timeout.load_config", return_value=base_config), \
         patch("cronwatch.cli_timeout.parse_jobs", return_value=base_config["jobs"]), \
         patch("cronwatch.cli_timeout.get_timeout_policy",
               return_value=TimeoutPolicy(seconds=30)), \
         patch("cronwatch.cli_timeout.run_job_with_timeout", return_value=timed_out):

        result = runner.invoke(cmd_timeout_run, ["backup"])

    assert result.exit_code == 1
    assert "timed out" in result.output.lower() or "timeout" in result.output.lower()


# ---------------------------------------------------------------------------
# cmd_timeout_run — unknown job
# ---------------------------------------------------------------------------

def test_cmd_timeout_run_unknown_job(runner, base_config):
    """Requesting an unknown job name prints an error and exits non-zero."""
    with patch("cronwatch.cli_timeout.load_config", return_value=base_config), \
         patch("cronwatch.cli_timeout.parse_jobs", return_value=base_config["jobs"]):

        result = runner.invoke(cmd_timeout_run, ["nonexistent-job"])

    assert result.exit_code != 0
    assert "nonexistent-job" in result.output or "not found" in result.output.lower()


# ---------------------------------------------------------------------------
# cmd_timeout_run — override flag
# ---------------------------------------------------------------------------

def test_cmd_timeout_run_override_seconds(runner, base_config):
    """--seconds flag overrides the configured timeout value."""
    ok = _result("backup", exit_code=0)
    captured = {}

    def fake_run(job, policy):
        captured["policy"] = policy
        return ok

    with patch("cronwatch.cli_timeout.load_config", return_value=base_config), \
         patch("cronwatch.cli_timeout.parse_jobs", return_value=base_config["jobs"]), \
         patch("cronwatch.cli_timeout.get_timeout_policy",
               return_value=TimeoutPolicy(seconds=30)), \
         patch("cronwatch.cli_timeout.run_job_with_timeout", side_effect=fake_run):

        result = runner.invoke(cmd_timeout_run, ["backup", "--seconds", "120"])

    assert result.exit_code == 0
    assert captured["policy"].seconds == 120

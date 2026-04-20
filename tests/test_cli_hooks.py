"""Tests for cronwatch.cli_hooks."""

from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from cronwatch.cli_hooks import hooks


@pytest.fixture()
def runner():
    return CliRunner()


_BASE_CONFIG = {
    "jobs": [
        {
            "name": "backup",
            "schedule": "0 2 * * *",
            "command": "tar czf /tmp/b.tgz /data",
            "hooks": {"pre": ["echo pre"], "on_failure": ["echo fail"]},
        }
    ],
    "hooks": {"timeout": 20},
}


def test_cmd_show_hooks_displays_policy(runner):
    with patch("cronwatch.cli_hooks.load_config", return_value=_BASE_CONFIG):
        result = runner.invoke(hooks, ["show", "backup"])
    assert result.exit_code == 0
    assert "pre" in result.output
    assert "echo pre" in result.output
    assert "20s" in result.output


def test_cmd_show_hooks_unknown_job_exits_1(runner):
    with patch("cronwatch.cli_hooks.load_config", return_value=_BASE_CONFIG):
        result = runner.invoke(hooks, ["show", "nonexistent"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_cmd_test_hooks_all_pass(runner):
    with patch("cronwatch.cli_hooks.load_config", return_value=_BASE_CONFIG), \
         patch("cronwatch.cli_hooks.run_hooks", return_value=[True]) as mock_run:
        result = runner.invoke(hooks, ["test", "backup", "--phase", "pre"])
    assert result.exit_code == 0
    assert "OK" in result.output
    mock_run.assert_called_once()


def test_cmd_test_hooks_failure_exits_1(runner):
    with patch("cronwatch.cli_hooks.load_config", return_value=_BASE_CONFIG), \
         patch("cronwatch.cli_hooks.run_hooks", return_value=[False]):
        result = runner.invoke(hooks, ["test", "backup", "--phase", "pre"])
    assert result.exit_code == 1
    assert "FAIL" in result.output


def test_cmd_test_hooks_no_hooks_configured(runner):
    with patch("cronwatch.cli_hooks.load_config", return_value=_BASE_CONFIG):
        result = runner.invoke(hooks, ["test", "backup", "--phase", "post"])
    assert result.exit_code == 0
    assert "No 'post' hooks" in result.output


def test_cmd_test_hooks_unknown_job_exits_1(runner):
    with patch("cronwatch.cli_hooks.load_config", return_value=_BASE_CONFIG):
        result = runner.invoke(hooks, ["test", "ghost", "--phase", "pre"])
    assert result.exit_code == 1

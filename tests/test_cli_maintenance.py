"""Tests for cronwatch.cli_maintenance."""

from datetime import datetime, time
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from cronwatch.cli_maintenance import (
    cmd_check_maintenance,
    cmd_maintenance_status,
    cmd_show_maintenance,
)


@pytest.fixture()
def runner():
    return CliRunner()


def _cfg(extra_jobs=None, maintenance=None):
    jobs = extra_jobs or [
        {"name": "backup", "schedule": "0 2 * * *", "command": "tar -czf /tmp/b.tgz /data"},
    ]
    cfg = {"jobs": jobs}
    if maintenance:
        cfg["maintenance"] = maintenance
    return cfg


# ---------------------------------------------------------------------------
# cmd_maintenance_status
# ---------------------------------------------------------------------------

def test_cmd_maintenance_status_inactive(runner):
    cfg = _cfg()
    with patch("cronwatch.cli_maintenance.load_config", return_value=cfg):
        result = runner.invoke(cmd_maintenance_status, [])
    assert result.exit_code == 0
    assert "inactive" in result.output


def test_cmd_maintenance_status_active(runner):
    now = datetime(2024, 1, 1, 3, 0)  # 03:00 Monday
    cfg = _cfg(maintenance=[{"start": "02:00", "end": "04:00"}])
    with patch("cronwatch.cli_maintenance.load_config", return_value=cfg), \
         patch("cronwatch.cli_maintenance.datetime") as mock_dt:
        mock_dt.now.return_value = now
        result = runner.invoke(cmd_maintenance_status, [])
    assert result.exit_code == 0
    assert "ACTIVE" in result.output


# ---------------------------------------------------------------------------
# cmd_show_maintenance
# ---------------------------------------------------------------------------

def test_cmd_show_maintenance_no_windows(runner):
    cfg = _cfg()
    with patch("cronwatch.cli_maintenance.load_config", return_value=cfg):
        result = runner.invoke(cmd_show_maintenance, ["backup"])
    assert result.exit_code == 0
    assert "No maintenance" in result.output


def test_cmd_show_maintenance_with_global_window(runner):
    cfg = _cfg(maintenance=[{"start": "01:00", "end": "03:00"}])
    with patch("cronwatch.cli_maintenance.load_config", return_value=cfg):
        result = runner.invoke(cmd_show_maintenance, ["backup"])
    assert result.exit_code == 0
    assert "Global windows" in result.output


def test_cmd_show_maintenance_with_job_window(runner):
    jobs = [
        {
            "name": "backup",
            "schedule": "0 2 * * *",
            "command": "tar",
            "maintenance": [{"start": "05:00", "end": "06:00"}],
        }
    ]
    cfg = _cfg(extra_jobs=jobs)
    with patch("cronwatch.cli_maintenance.load_config", return_value=cfg):
        result = runner.invoke(cmd_show_maintenance, ["backup"])
    assert result.exit_code == 0
    assert "Job-level" in result.output


def test_cmd_show_maintenance_unknown_job_exits_1(runner):
    cfg = _cfg()
    with patch("cronwatch.cli_maintenance.load_config", return_value=cfg):
        result = runner.invoke(cmd_show_maintenance, ["ghost"])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# cmd_check_maintenance
# ---------------------------------------------------------------------------

def test_cmd_check_maintenance_inactive_exits_1(runner):
    cfg = _cfg()
    with patch("cronwatch.cli_maintenance.load_config", return_value=cfg):
        result = runner.invoke(cmd_check_maintenance, ["backup"])
    assert result.exit_code == 1
    assert "inactive" in result.output


def test_cmd_check_maintenance_active_exits_0(runner):
    now = datetime(2024, 1, 1, 3, 0)
    jobs = [
        {
            "name": "backup",
            "schedule": "0 2 * * *",
            "command": "tar",
            "maintenance": [{"start": "02:00", "end": "04:00"}],
        }
    ]
    cfg = _cfg(extra_jobs=jobs)
    with patch("cronwatch.cli_maintenance.load_config", return_value=cfg), \
         patch("cronwatch.maintenance.datetime") as mock_dt:
        mock_dt.now.return_value = now
        result = runner.invoke(cmd_check_maintenance, ["backup"])
    assert result.exit_code == 0


def test_cmd_check_maintenance_unknown_job_exits_2(runner):
    cfg = _cfg()
    with patch("cronwatch.cli_maintenance.load_config", return_value=cfg):
        result = runner.invoke(cmd_check_maintenance, ["ghost"])
    assert result.exit_code == 2

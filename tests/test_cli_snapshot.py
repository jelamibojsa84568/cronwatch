"""Tests for cronwatch.cli_snapshot."""

import json
import os
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from cronwatch.cli_snapshot import cmd_capture, cmd_diff, cmd_show


@pytest.fixture()
def runner():
    return CliRunner()


BASE_CONFIG = {
    "log_dir": "",  # filled per test
    "jobs": [
        {"name": "backup", "schedule": "0 2 * * *", "command": "/bin/backup.sh"},
    ],
}


def _cfg(tmp_path):
    cfg = dict(BASE_CONFIG)
    cfg["log_dir"] = str(tmp_path)
    return cfg


def test_cmd_capture_exits_0(runner, tmp_path):
    with patch("cronwatch.cli_snapshot.load_config", return_value=_cfg(tmp_path)):
        result = runner.invoke(cmd_capture, [])
    assert result.exit_code == 0


def test_cmd_capture_reports_job_count(runner, tmp_path):
    with patch("cronwatch.cli_snapshot.load_config", return_value=_cfg(tmp_path)):
        result = runner.invoke(cmd_capture, [])
    assert "1 job(s)" in result.output


def test_cmd_capture_creates_snapshot_file(runner, tmp_path):
    with patch("cronwatch.cli_snapshot.load_config", return_value=_cfg(tmp_path)):
        runner.invoke(cmd_capture, [])
    snap_path = tmp_path / "snapshots" / "job_snapshot.json"
    assert snap_path.exists()


def test_cmd_diff_no_snapshot_exits_1(runner, tmp_path):
    with patch("cronwatch.cli_snapshot.load_config", return_value=_cfg(tmp_path)):
        result = runner.invoke(cmd_diff, [])
    assert result.exit_code == 1
    assert "No previous snapshot" in result.output


def test_cmd_diff_no_changes(runner, tmp_path):
    cfg = _cfg(tmp_path)
    with patch("cronwatch.cli_snapshot.load_config", return_value=cfg):
        runner.invoke(cmd_capture, [])
    with patch("cronwatch.cli_snapshot.load_config", return_value=cfg):
        result = runner.invoke(cmd_diff, [])
    assert result.exit_code == 0
    assert "No changes" in result.output


def test_cmd_diff_detects_added_job(runner, tmp_path):
    cfg_old = _cfg(tmp_path)
    with patch("cronwatch.cli_snapshot.load_config", return_value=cfg_old):
        runner.invoke(cmd_capture, [])

    cfg_new = dict(cfg_old)
    cfg_new["jobs"] = cfg_old["jobs"] + [
        {"name": "cleanup", "schedule": "0 3 * * *", "command": "/bin/cleanup.sh"}
    ]
    with patch("cronwatch.cli_snapshot.load_config", return_value=cfg_new):
        result = runner.invoke(cmd_diff, [])
    assert "cleanup" in result.output
    assert "Added" in result.output


def test_cmd_show_no_snapshot_exits_1(runner, tmp_path):
    with patch("cronwatch.cli_snapshot.load_config", return_value=_cfg(tmp_path)):
        result = runner.invoke(cmd_show, [])
    assert result.exit_code == 1


def test_cmd_show_displays_job_names(runner, tmp_path):
    cfg = _cfg(tmp_path)
    with patch("cronwatch.cli_snapshot.load_config", return_value=cfg):
        runner.invoke(cmd_capture, [])
    with patch("cronwatch.cli_snapshot.load_config", return_value=cfg):
        result = runner.invoke(cmd_show, [])
    assert "backup" in result.output
    assert result.exit_code == 0

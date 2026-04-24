"""Tests for cronwatch.janitor."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from cronwatch.janitor import (
    DEFAULT_HISTORY_MAX_AGE_DAYS,
    DEFAULT_LOG_MAX_AGE_DAYS,
    DEFAULT_METRICS_MAX_AGE_DAYS,
    get_janitor_policy,
    run_janitor,
)


# ---------------------------------------------------------------------------
# get_janitor_policy
# ---------------------------------------------------------------------------

def test_get_janitor_policy_defaults():
    policy = get_janitor_policy({})
    assert policy["log_max_age_days"] == DEFAULT_LOG_MAX_AGE_DAYS
    assert policy["history_max_age_days"] == DEFAULT_HISTORY_MAX_AGE_DAYS
    assert policy["metrics_max_age_days"] == DEFAULT_METRICS_MAX_AGE_DAYS
    assert policy["dry_run"] is False


def test_get_janitor_policy_custom_values():
    config = {"janitor": {"log_max_age_days": 7, "history_max_age_days": 14, "dry_run": True}}
    policy = get_janitor_policy(config)
    assert policy["log_max_age_days"] == 7
    assert policy["history_max_age_days"] == 14
    assert policy["dry_run"] is True
    # metrics falls back to default
    assert policy["metrics_max_age_days"] == DEFAULT_METRICS_MAX_AGE_DAYS


def test_get_janitor_policy_string_int_coercion():
    config = {"janitor": {"log_max_age_days": "5"}}
    policy = get_janitor_policy(config)
    assert policy["log_max_age_days"] == 5


# ---------------------------------------------------------------------------
# run_janitor
# ---------------------------------------------------------------------------

@pytest.fixture()
def dirs(tmp_path):
    log_dir = tmp_path / "logs"
    history_dir = tmp_path / "history"
    metrics_dir = tmp_path / "metrics"
    for d in (log_dir, history_dir, metrics_dir):
        d.mkdir()
    return log_dir, history_dir, metrics_dir


def _touch_old(path: Path, age_days: float = 40):
    path.write_text("x")
    old_time = time.time() - age_days * 86400
    import os
    os.utime(path, (old_time, old_time))


def _make_config(log_dir, history_dir, metrics_dir, extra=None):
    cfg = {
        "log_dir": str(log_dir),
        "history_dir": str(history_dir),
        "metrics_dir": str(metrics_dir),
    }
    if extra:
        cfg.update(extra)
    return cfg


def test_run_janitor_removes_old_logs(dirs):
    log_dir, history_dir, metrics_dir = dirs
    old_log = log_dir / "backup.log"
    _touch_old(old_log)
    config = _make_config(log_dir, history_dir, metrics_dir)
    summary = run_janitor(config)
    assert str(old_log) in summary["logs"]
    assert not old_log.exists()


def test_run_janitor_keeps_recent_logs(dirs):
    log_dir, history_dir, metrics_dir = dirs
    recent = log_dir / "recent.log"
    recent.write_text("new")
    config = _make_config(log_dir, history_dir, metrics_dir)
    summary = run_janitor(config)
    assert str(recent) not in summary["logs"]
    assert recent.exists()


def test_run_janitor_dry_run_does_not_delete(dirs):
    log_dir, history_dir, metrics_dir = dirs
    old_log = log_dir / "old.log"
    _touch_old(old_log)
    config = _make_config(log_dir, history_dir, metrics_dir, {"janitor": {"dry_run": True}})
    summary = run_janitor(config)
    assert str(old_log) in summary["logs"]
    assert old_log.exists()  # not actually deleted


def test_run_janitor_ignores_non_matching_suffix(dirs):
    log_dir, history_dir, metrics_dir = dirs
    old_txt = log_dir / "old.txt"
    _touch_old(old_txt)
    config = _make_config(log_dir, history_dir, metrics_dir)
    summary = run_janitor(config)
    assert str(old_txt) not in summary["logs"]
    assert old_txt.exists()


def test_run_janitor_missing_directory_returns_empty(tmp_path):
    config = {
        "log_dir": str(tmp_path / "no_logs"),
        "history_dir": str(tmp_path / "no_history"),
        "metrics_dir": str(tmp_path / "no_metrics"),
    }
    summary = run_janitor(config)
    assert summary["logs"] == []
    assert summary["history"] == []
    assert summary["metrics"] == []

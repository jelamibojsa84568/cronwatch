"""Tests for cronwatch.config module."""

import os
from pathlib import Path

import pytest
import yaml

from cronwatch.config import (
    DEFAULT_CONFIG,
    load_config,
    save_default_config,
)


def test_load_config_returns_defaults_when_no_file(tmp_path):
    """load_config should return defaults when the config file is absent."""
    non_existent = tmp_path / "missing.yaml"
    config = load_config(non_existent.parent / "also_missing.yaml") if False else load_config.__wrapped__ if False else None
    # Use a path that simply doesn't exist (no explicit path → won't raise).
    config = load_config(tmp_path / "no_config.yaml")  # file absent, no raise
    assert config["retention_days"] == DEFAULT_CONFIG["retention_days"]
    assert config["alert_on_failure"] is True


def test_load_config_merges_user_values(tmp_path):
    """User values should override defaults."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.safe_dump({"retention_days": 7, "alert_on_failure": False}))

    config = load_config(config_file)

    assert config["retention_days"] == 7
    assert config["alert_on_failure"] is False
    # Keys not in user file should still be present from defaults.
    assert "log_dir" in config


def test_load_config_raises_for_missing_explicit_path(tmp_path):
    """load_config should raise FileNotFoundError for an explicit missing path."""
    missing = tmp_path / "ghost.yaml"
    with pytest.raises(FileNotFoundError, match="ghost.yaml"):
        load_config(missing)


def test_load_config_invalid_yaml_raises(tmp_path):
    """load_config should propagate YAML parse errors."""
    bad_file = tmp_path / "bad.yaml"
    bad_file.write_text("retention_days: [unclosed")

    with pytest.raises(Exception):  # yaml.YAMLError or scanner error
        load_config(bad_file)


def test_env_override_log_dir(tmp_path, monkeypatch):
    """CRONWATCH_LOG_DIR env var should override log_dir."""
    monkeypatch.setenv("CRONWATCH_LOG_DIR", "/tmp/custom_logs")
    config = load_config(tmp_path / "absent.yaml")
    assert config["log_dir"] == "/tmp/custom_logs"


def test_save_default_config_creates_file(tmp_path):
    """save_default_config should write a valid YAML file."""
    dest = tmp_path / "subdir" / "config.yaml"
    returned_path = save_default_config(dest)

    assert returned_path == dest
    assert dest.exists()

    with dest.open() as fh:
        written = yaml.safe_load(fh)

    assert written["retention_days"] == DEFAULT_CONFIG["retention_days"]
    assert written["alert_on_failure"] == DEFAULT_CONFIG["alert_on_failure"]

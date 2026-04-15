"""Tests for cronwatch.alerts throttle and dispatch logic."""

import json
import time
from pathlib import Path

import pytest

from cronwatch.alerts import (
    is_throttled,
    record_alert_sent,
    clear_alert_state,
    maybe_send_alert,
    _state_path,
)


@pytest.fixture
def state_dir(tmp_path):
    return str(tmp_path / "alert_state")


def test_is_throttled_returns_false_when_no_state(state_dir):
    assert is_throttled("backup", state_dir) is False


def test_record_alert_sent_creates_state_file(state_dir):
    record_alert_sent("backup", state_dir)
    assert _state_path(state_dir).exists()


def test_record_alert_sent_stores_timestamp(state_dir):
    before = time.time()
    record_alert_sent("backup", state_dir)
    after = time.time()
    state = json.loads(_state_path(state_dir).read_text())
    assert before <= state["backup"] <= after


def test_is_throttled_true_immediately_after_send(state_dir):
    record_alert_sent("backup", state_dir)
    assert is_throttled("backup", state_dir, throttle_seconds=3600) is True


def test_is_throttled_false_after_window_expires(state_dir):
    record_alert_sent("backup", state_dir)
    # Manually backdate the timestamp
    state = json.loads(_state_path(state_dir).read_text())
    state["backup"] = time.time() - 7200
    _state_path(state_dir).write_text(json.dumps(state))
    assert is_throttled("backup", state_dir, throttle_seconds=3600) is False


def test_clear_alert_state_removes_job(state_dir):
    record_alert_sent("backup", state_dir)
    clear_alert_state("backup", state_dir)
    assert is_throttled("backup", state_dir) is False


def test_clear_alert_state_ignores_missing_job(state_dir):
    clear_alert_state("nonexistent", state_dir)  # should not raise


def test_maybe_send_alert_calls_send_fn_when_not_throttled(state_dir):
    called = []
    result = maybe_send_alert("job1", lambda: called.append(True), state_dir, throttle_seconds=3600)
    assert result is True
    assert called == [True]


def test_maybe_send_alert_skips_send_fn_when_throttled(state_dir):
    record_alert_sent("job1", state_dir)
    called = []
    result = maybe_send_alert("job1", lambda: called.append(True), state_dir, throttle_seconds=3600)
    assert result is False
    assert called == []


def test_maybe_send_alert_records_state_after_send(state_dir):
    maybe_send_alert("job2", lambda: None, state_dir, throttle_seconds=3600)
    assert is_throttled("job2", state_dir, throttle_seconds=3600) is True


def test_is_throttled_handles_corrupt_state_file(state_dir):
    path = _state_path(state_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not valid json")
    assert is_throttled("backup", state_dir) is False

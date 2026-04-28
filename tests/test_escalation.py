"""Tests for cronwatch.escalation."""

from __future__ import annotations

import time
import pytest

from cronwatch.escalation import (
    DEFAULT_INTERVAL,
    DEFAULT_THRESHOLD,
    get_escalation_policy,
    record_failure,
    record_success,
    record_escalation_sent,
    should_escalate,
)


# ---------------------------------------------------------------------------
# get_escalation_policy
# ---------------------------------------------------------------------------

def test_get_escalation_policy_defaults():
    policy = get_escalation_policy({}, {})
    assert policy["threshold"] == DEFAULT_THRESHOLD
    assert policy["interval"] == DEFAULT_INTERVAL
    assert policy["enabled"] is True


def test_get_escalation_policy_global_config():
    config = {"escalation": {"threshold": 5, "interval": 7200}}
    policy = get_escalation_policy({}, config)
    assert policy["threshold"] == 5
    assert policy["interval"] == 7200


def test_get_escalation_policy_global_int_shorthand():
    config = {"escalation": 2}
    policy = get_escalation_policy({}, config)
    assert policy["threshold"] == 2


def test_get_escalation_policy_job_overrides_global():
    config = {"escalation": {"threshold": 5, "interval": 7200}}
    job = {"escalation": {"threshold": 1}}
    policy = get_escalation_policy(job, config)
    assert policy["threshold"] == 1
    assert policy["interval"] == 7200  # inherited from global


def test_get_escalation_policy_job_int_shorthand():
    job = {"escalation": 10}
    policy = get_escalation_policy(job, {})
    assert policy["threshold"] == 10


def test_get_escalation_policy_disabled():
    policy = get_escalation_policy({"escalation": {"enabled": False}}, {})
    assert policy["enabled"] is False


# ---------------------------------------------------------------------------
# record_failure / record_success
# ---------------------------------------------------------------------------

def test_record_failure_increments(tmp_path):
    assert record_failure(tmp_path, "myjob") == 1
    assert record_failure(tmp_path, "myjob") == 2


def test_record_success_resets_count(tmp_path):
    record_failure(tmp_path, "myjob")
    record_failure(tmp_path, "myjob")
    record_success(tmp_path, "myjob")
    # next failure starts from 1 again
    assert record_failure(tmp_path, "myjob") == 1


# ---------------------------------------------------------------------------
# should_escalate
# ---------------------------------------------------------------------------

def test_should_escalate_false_below_threshold(tmp_path):
    policy = {"enabled": True, "threshold": 3, "interval": 60}
    record_failure(tmp_path, "job")
    record_failure(tmp_path, "job")
    assert should_escalate(tmp_path, "job", policy) is False


def test_should_escalate_true_at_threshold(tmp_path):
    policy = {"enabled": True, "threshold": 2, "interval": 0}
    record_failure(tmp_path, "job")
    record_failure(tmp_path, "job")
    assert should_escalate(tmp_path, "job", policy) is True


def test_should_escalate_false_within_interval(tmp_path):
    policy = {"enabled": True, "threshold": 1, "interval": 9999}
    record_failure(tmp_path, "job")
    record_escalation_sent(tmp_path, "job")
    assert should_escalate(tmp_path, "job", policy) is False


def test_should_escalate_true_after_interval(tmp_path, monkeypatch):
    policy = {"enabled": True, "threshold": 1, "interval": 1}
    record_failure(tmp_path, "job")
    record_escalation_sent(tmp_path, "job")
    # advance time
    monkeypatch.setattr("cronwatch.escalation.time.time", lambda: time.time() + 5)
    assert should_escalate(tmp_path, "job", policy) is True


def test_should_escalate_false_when_disabled(tmp_path):
    policy = {"enabled": False, "threshold": 1, "interval": 0}
    record_failure(tmp_path, "job")
    assert should_escalate(tmp_path, "job", policy) is False

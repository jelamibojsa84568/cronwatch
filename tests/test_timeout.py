"""Tests for cronwatch.timeout."""
import time
import pytest
from cronwatch.timeout import (
    JobTimeoutError,
    TimeoutPolicy,
    get_timeout_policy,
    timeout_context,
)


def test_timeout_policy_enabled():
    assert TimeoutPolicy(seconds=10).is_enabled() is True


def test_timeout_policy_disabled_none():
    assert TimeoutPolicy(seconds=None).is_enabled() is False


def test_timeout_policy_disabled_zero():
    assert TimeoutPolicy(seconds=0).is_enabled() is False


def test_get_timeout_policy_job_level():
    job = {"name": "j", "timeout": 30}
    policy = get_timeout_policy(job, {})
    assert policy.seconds == 30


def test_get_timeout_policy_global_fallback():
    job = {"name": "j"}
    config = {"defaults": {"timeout": 60}}
    policy = get_timeout_policy(job, config)
    assert policy.seconds == 60


def test_get_timeout_policy_job_overrides_global():
    job = {"name": "j", "timeout": 5}
    config = {"defaults": {"timeout": 60}}
    policy = get_timeout_policy(job, config)
    assert policy.seconds == 5


def test_get_timeout_policy_no_timeout():
    policy = get_timeout_policy({"name": "j"}, {})
    assert policy.seconds is None
    assert policy.is_enabled() is False


def test_timeout_context_no_timeout_passes():
    policy = TimeoutPolicy(seconds=None)
    with timeout_context("job", policy):
        time.sleep(0.01)  # should not raise


def test_timeout_context_completes_within_limit():
    policy = TimeoutPolicy(seconds=5)
    with timeout_context("job", policy):
        time.sleep(0.01)  # well within limit


def test_timeout_context_raises_on_exceed():
    policy = TimeoutPolicy(seconds=1)
    with pytest.raises(JobTimeoutError) as exc_info:
        with timeout_context("slow_job", policy):
            time.sleep(3)
    assert exc_info.value.job_name == "slow_job"
    assert exc_info.value.timeout == 1


def test_job_timeout_error_message():
    err = JobTimeoutError("backup", 120)
    assert "backup" in str(err)
    assert "120" in str(err)

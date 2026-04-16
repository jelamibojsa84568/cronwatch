"""Tests for cronwatch.retry."""
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.retry import RetryPolicy, RetryOutcome, get_retry_policy, run_with_retry
from cronwatch.runner import JobResult


JOB = {"name": "myjob", "command": "echo hi"}


def _make_result(name, exit_code):
    return JobResult(job_name=name, command="echo hi", exit_code=exit_code,
                     stdout="", stderr="", duration=0.1)


def test_get_retry_policy_defaults():
    policy = get_retry_policy({"name": "j", "command": "x"}, {})
    assert policy.max_attempts == 3
    assert policy.delay_seconds == 5.0
    assert policy.backoff_factor == 2.0


def test_get_retry_policy_global_config():
    config = {"retry": {"max_attempts": 5, "delay_seconds": 10.0}}
    policy = get_retry_policy(JOB, config)
    assert policy.max_attempts == 5
    assert policy.delay_seconds == 10.0


def test_get_retry_policy_job_overrides_global():
    config = {"retry": {"max_attempts": 5}}
    job = {**JOB, "retry": {"max_attempts": 2}}
    policy = get_retry_policy(job, config)
    assert policy.max_attempts == 2


def test_run_with_retry_succeeds_first_attempt():
    policy = RetryPolicy(max_attempts=3, delay_seconds=0)
    sleep_mock = MagicMock()
    with patch("cronwatch.retry.run_job", return_value=_make_result("myjob", 0)):
        outcome = run_with_retry(JOB, policy, _sleep=sleep_mock)
    assert outcome.succeeded is True
    assert outcome.attempts == 1
    sleep_mock.assert_not_called()


def test_run_with_retry_retries_on_failure():
    policy = RetryPolicy(max_attempts=3, delay_seconds=1.0, backoff_factor=2.0)
    sleep_mock = MagicMock()
    fail = _make_result("myjob", 1)
    ok = _make_result("myjob", 0)
    with patch("cronwatch.retry.run_job", side_effect=[fail, fail, ok]):
        outcome = run_with_retry(JOB, policy, _sleep=sleep_mock)
    assert outcome.succeeded is True
    assert outcome.attempts == 3
    assert sleep_mock.call_count == 2


def test_run_with_retry_exhausts_attempts():
    policy = RetryPolicy(max_attempts=2, delay_seconds=0)
    sleep_mock = MagicMock()
    fail = _make_result("myjob", 1)
    with patch("cronwatch.retry.run_job", return_value=fail):
        outcome = run_with_retry(JOB, policy, _sleep=sleep_mock)
    assert outcome.succeeded is False
    assert outcome.attempts == 2


def test_run_with_retry_backoff_delays():
    policy = RetryPolicy(max_attempts=3, delay_seconds=2.0, backoff_factor=3.0)
    sleep_mock = MagicMock()
    fail = _make_result("myjob", 1)
    with patch("cronwatch.retry.run_job", return_value=fail):
        outcome = run_with_retry(JOB, policy, _sleep=sleep_mock)
    assert outcome.delays == [2.0, 6.0]
    calls = [c[0][0] for c in sleep_mock.call_args_list]
    assert calls == [2.0, 6.0]


def test_retry_outcome_repr_succeeded():
    result = _make_result("myjob", 0)
    o = RetryOutcome(job_name="myjob", attempts=1, final_result=result, succeeded=True)
    assert "succeeded" in repr(o)
    assert "myjob" in repr(o)


def test_retry_outcome_repr_failed():
    result = _make_result("myjob", 1)
    o = RetryOutcome(job_name="myjob", attempts=3, final_result=result, succeeded=False)
    assert "failed" in repr(o)

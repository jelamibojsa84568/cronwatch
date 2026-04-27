"""Tests for cronwatch.healthcheck."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cronwatch.healthcheck import (
    HealthCheckPolicy,
    get_healthcheck_policy,
    ping_failure,
    ping_start,
    ping_success,
)


# ---------------------------------------------------------------------------
# get_healthcheck_policy
# ---------------------------------------------------------------------------

def test_get_healthcheck_policy_defaults_empty():
    policy = get_healthcheck_policy({}, {})
    assert policy.url is None
    assert policy.is_enabled() is False
    assert policy.ping_start is False
    assert policy.ping_failure is True
    assert policy.timeout_seconds == 10


def test_get_healthcheck_policy_global_url():
    config = {"healthcheck": {"url": "https://hc.example.com/abc"}}
    policy = get_healthcheck_policy(config, {})
    assert policy.url == "https://hc.example.com/abc"
    assert policy.is_enabled() is True


def test_get_healthcheck_policy_job_string_shorthand():
    policy = get_healthcheck_policy({}, {"healthcheck": "https://hc.example.com/xyz"})
    assert policy.url == "https://hc.example.com/xyz"
    assert policy.is_enabled() is True


def test_get_healthcheck_policy_job_overrides_global():
    config = {"healthcheck": {"url": "https://hc.example.com/global", "ping_start": False}}
    job = {"healthcheck": {"url": "https://hc.example.com/job", "ping_start": True}}
    policy = get_healthcheck_policy(config, job)
    assert policy.url == "https://hc.example.com/job"
    assert policy.ping_start is True


def test_get_healthcheck_policy_timeout_coercion():
    policy = get_healthcheck_policy({"healthcheck": {"timeout_seconds": "30"}}, {})
    assert policy.timeout_seconds == 30


def test_get_healthcheck_policy_ping_failure_false():
    policy = get_healthcheck_policy({"healthcheck": {"ping_failure": False}}, {})
    assert policy.ping_failure is False


# ---------------------------------------------------------------------------
# ping helpers
# ---------------------------------------------------------------------------

def _mock_response(status: int) -> MagicMock:
    resp = MagicMock()
    resp.status = status
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def test_ping_success_returns_true_on_200():
    policy = HealthCheckPolicy(url="https://hc.example.com/abc")
    with patch("urllib.request.urlopen", return_value=_mock_response(200)):
        assert ping_success(policy) is True


def test_ping_success_disabled_returns_false():
    policy = HealthCheckPolicy(url=None)
    assert ping_success(policy) is False


def test_ping_start_appends_start_path():
    policy = HealthCheckPolicy(url="https://hc.example.com/abc", ping_start=True)
    with patch("urllib.request.urlopen", return_value=_mock_response(200)) as mock_open:
        ping_start(policy)
        called_url = mock_open.call_args[0][0]
        assert called_url.endswith("/start")


def test_ping_start_disabled_when_flag_false():
    policy = HealthCheckPolicy(url="https://hc.example.com/abc", ping_start=False)
    with patch("urllib.request.urlopen") as mock_open:
        result = ping_start(policy)
        mock_open.assert_not_called()
        assert result is False


def test_ping_failure_appends_fail_path():
    policy = HealthCheckPolicy(url="https://hc.example.com/abc", ping_failure=True)
    with patch("urllib.request.urlopen", return_value=_mock_response(200)) as mock_open:
        ping_failure(policy)
        called_url = mock_open.call_args[0][0]
        assert called_url.endswith("/fail")


def test_ping_returns_false_on_network_error():
    policy = HealthCheckPolicy(url="https://hc.example.com/abc")
    with patch("urllib.request.urlopen", side_effect=OSError("network down")):
        assert ping_success(policy) is False

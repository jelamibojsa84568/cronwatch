"""Tests for cronwatch.webhook."""

from __future__ import annotations

from unittest.mock import patch, MagicMock
import pytest

from cronwatch.webhook import (
    WebhookPolicy,
    get_webhook_policy,
    build_payload,
    send_webhook,
)
from cronwatch.runner import JobResult


def _result(success: bool = False) -> JobResult:
    return JobResult(
        job_name="backup",
        exit_code=0 if success else 1,
        stdout="out",
        stderr="" if success else "err",
        duration=1.5,
        started_at="2024-01-01T00:00:00",
    )


# --- get_webhook_policy ---

def test_get_webhook_policy_defaults():
    policy = get_webhook_policy({}, {})
    assert policy.url is None
    assert policy.on_failure is True
    assert policy.on_success is False
    assert policy.timeout == 10
    assert policy.secret_header is None


def test_get_webhook_policy_global_url():
    config = {"webhook": {"url": "https://example.com/hook"}}
    policy = get_webhook_policy({}, config)
    assert policy.url == "https://example.com/hook"


def test_get_webhook_policy_string_shorthand():
    config = {"webhook": "https://example.com/hook"}
    policy = get_webhook_policy({}, config)
    assert policy.url == "https://example.com/hook"


def test_get_webhook_policy_job_overrides_global():
    config = {"webhook": {"url": "https://global.example.com/hook", "timeout": 5}}
    job = {"webhook": {"url": "https://job.example.com/hook", "on_success": True}}
    policy = get_webhook_policy(job, config)
    assert policy.url == "https://job.example.com/hook"
    assert policy.on_success is True
    assert policy.timeout == 5  # inherited from global


def test_get_webhook_policy_is_enabled_no_url():
    policy = get_webhook_policy({}, {})
    assert policy.is_enabled() is False


def test_get_webhook_policy_is_enabled_with_url():
    policy = get_webhook_policy({}, {"webhook": {"url": "https://x.com"}})
    assert policy.is_enabled() is True


# --- build_payload ---

def test_build_payload_contains_job_name():
    payload = build_payload(_result())
    assert payload["job"] == "backup"


def test_build_payload_reflects_success_flag():
    assert build_payload(_result(success=True))["success"] is True
    assert build_payload(_result(success=False))["success"] is False


def test_build_payload_contains_exit_code():
    payload = build_payload(_result(success=False))
    assert payload["exit_code"] == 1


# --- send_webhook ---

def test_send_webhook_skips_when_disabled():
    policy = WebhookPolicy(url=None, on_failure=True, on_success=False, timeout=5, secret_header=None)
    assert send_webhook(_result(), policy) is False


def test_send_webhook_skips_success_when_not_configured():
    policy = WebhookPolicy(url="https://x.com", on_failure=True, on_success=False, timeout=5, secret_header=None)
    assert send_webhook(_result(success=True), policy) is False


def test_send_webhook_posts_on_failure():
    policy = WebhookPolicy(url="https://x.com", on_failure=True, on_success=False, timeout=5, secret_header=None)
    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.status = 200
    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = send_webhook(_result(success=False), policy)
    assert result is True


def test_send_webhook_returns_false_on_network_error():
    import urllib.error
    policy = WebhookPolicy(url="https://x.com", on_failure=True, on_success=False, timeout=5, secret_header=None)
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
        result = send_webhook(_result(success=False), policy)
    assert result is False

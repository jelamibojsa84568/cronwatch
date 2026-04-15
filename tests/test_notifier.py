"""Tests for cronwatch.notifier."""

import pytest
from unittest.mock import patch, MagicMock

from cronwatch.runner import JobResult
from cronwatch.notifier import build_failure_email, send_email_alert


@pytest.fixture()
def failed_result():
    return JobResult(
        job_name="backup-db",
        exit_code=1,
        stdout="backing up...",
        stderr="Error: disk full",
        duration=3.14,
    )


@pytest.fixture()
def success_result():
    return JobResult(
        job_name="backup-db",
        exit_code=0,
        stdout="done",
        stderr="",
        duration=1.0,
    )


@pytest.fixture()
def email_config():
    return {
        "alerts": {
            "email_enabled": True,
            "smtp_host": "localhost",
            "smtp_port": 25,
            "sender": "cronwatch@example.com",
            "recipient": "ops@example.com",
        }
    }


def test_build_failure_email_subject_contains_job_name(failed_result):
    msg = build_failure_email(failed_result, "ops@example.com", "cw@example.com", hostname="srv1")
    assert "backup-db" in msg["Subject"]
    assert "srv1" in msg["Subject"]


def test_build_failure_email_body_contains_exit_code(failed_result):
    msg = build_failure_email(failed_result, "ops@example.com", "cw@example.com")
    payload = msg.get_payload(0).get_payload()
    assert "1" in payload
    assert "Error: disk full" in payload


def test_build_failure_email_unknown_host_fallback(failed_result):
    msg = build_failure_email(failed_result, "ops@example.com", "cw@example.com")
    assert "unknown host" in msg["Subject"]


def test_send_email_alert_skips_when_disabled(failed_result, email_config):
    email_config["alerts"]["email_enabled"] = False
    result = send_email_alert(failed_result, email_config)
    assert result is False


def test_send_email_alert_skips_on_success(success_result, email_config):
    result = send_email_alert(success_result, email_config)
    assert result is False


def test_send_email_alert_sends_on_failure(failed_result, email_config):
    with patch("cronwatch.notifier.smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        result = send_email_alert(failed_result, email_config, hostname="srv1")

    assert result is True
    mock_server.sendmail.assert_called_once()


def test_send_email_alert_returns_false_on_smtp_error(failed_result, email_config):
    with patch("cronwatch.notifier.smtplib.SMTP", side_effect=OSError("connection refused")):
        result = send_email_alert(failed_result, email_config)

    assert result is False

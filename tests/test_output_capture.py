"""Tests for cronwatch.output_capture."""

import pytest

from cronwatch.output_capture import (
    CapturePolicy,
    collect_output,
    get_capture_policy,
    truncate_output,
)


# ---------------------------------------------------------------------------
# CapturePolicy defaults
# ---------------------------------------------------------------------------

def test_capture_policy_defaults():
    p = CapturePolicy()
    assert p.capture_stdout is True
    assert p.capture_stderr is True
    assert p.max_bytes == 10_240
    assert p.include_in_alerts is True


def test_capture_policy_is_capturing_true():
    assert CapturePolicy().is_capturing() is True


def test_capture_policy_is_capturing_false_when_both_disabled():
    p = CapturePolicy(capture_stdout=False, capture_stderr=False)
    assert p.is_capturing() is False


# ---------------------------------------------------------------------------
# get_capture_policy
# ---------------------------------------------------------------------------

def test_get_capture_policy_defaults_when_empty():
    policy = get_capture_policy({}, {})
    assert policy.capture_stdout is True
    assert policy.capture_stderr is True
    assert policy.max_bytes == 10_240


def test_get_capture_policy_global_config():
    config = {"output_capture": {"max_bytes": 512, "capture_stderr": False}}
    policy = get_capture_policy({}, config)
    assert policy.max_bytes == 512
    assert policy.capture_stderr is False
    assert policy.capture_stdout is True


def test_get_capture_policy_job_overrides_global():
    config = {"output_capture": {"max_bytes": 512, "capture_stderr": False}}
    job = {"output_capture": {"capture_stderr": True, "max_bytes": 1024}}
    policy = get_capture_policy(job, config)
    assert policy.capture_stderr is True
    assert policy.max_bytes == 1024


def test_get_capture_policy_include_in_alerts_false():
    config = {"output_capture": {"include_in_alerts": False}}
    policy = get_capture_policy({}, config)
    assert policy.include_in_alerts is False


# ---------------------------------------------------------------------------
# truncate_output
# ---------------------------------------------------------------------------

def test_truncate_output_no_truncation_needed():
    text = "hello world"
    assert truncate_output(text, 1000) == text


def test_truncate_output_empty_string():
    assert truncate_output("", 100) == ""


def test_truncate_output_truncates_long_text():
    text = "a" * 200
    result = truncate_output(text, 100)
    assert "[... output truncated ...]" in result
    assert len(result.encode("utf-8")) > 100  # includes notice
    assert result.startswith("a" * 100)


def test_truncate_output_exact_boundary():
    text = "b" * 50
    assert truncate_output(text, 50) == text


# ---------------------------------------------------------------------------
# collect_output
# ---------------------------------------------------------------------------

def test_collect_output_both_captured():
    policy = CapturePolicy(capture_stdout=True, capture_stderr=True, max_bytes=10_240)
    out = collect_output(policy, "out text", "err text")
    assert out["stdout"] == "out text"
    assert out["stderr"] == "err text"


def test_collect_output_only_stdout():
    policy = CapturePolicy(capture_stdout=True, capture_stderr=False)
    out = collect_output(policy, "out text", "err text")
    assert "stdout" in out
    assert "stderr" not in out


def test_collect_output_only_stderr():
    policy = CapturePolicy(capture_stdout=False, capture_stderr=True)
    out = collect_output(policy, "out text", "err text")
    assert "stderr" in out
    assert "stdout" not in out


def test_collect_output_none_values_handled():
    policy = CapturePolicy()
    out = collect_output(policy, None, None)
    assert out["stdout"] == ""
    assert out["stderr"] == ""

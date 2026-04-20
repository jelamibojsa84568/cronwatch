"""Tests for cronwatch.hooks."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.hooks import (
    HookPolicy,
    get_hook_policy,
    run_hooks,
    _run_hook,
)


# ---------------------------------------------------------------------------
# get_hook_policy
# ---------------------------------------------------------------------------

def test_get_hook_policy_defaults_empty():
    policy = get_hook_policy({}, {})
    assert policy.pre == []
    assert policy.post == []
    assert policy.on_failure == []
    assert policy.timeout == 30


def test_get_hook_policy_global_fallback():
    global_cfg = {"hooks": {"pre": ["echo start"], "timeout": 15}}
    policy = get_hook_policy({}, global_cfg)
    assert policy.pre == ["echo start"]
    assert policy.timeout == 15


def test_get_hook_policy_job_overrides_global():
    global_cfg = {"hooks": {"pre": ["echo global"], "on_failure": ["echo fail"]}}
    job_cfg = {"hooks": {"pre": ["echo job"]}}
    policy = get_hook_policy(job_cfg, global_cfg)
    assert policy.pre == ["echo job"]
    # on_failure not overridden — falls back to global
    assert policy.on_failure == ["echo fail"]


def test_get_hook_policy_string_converted_to_list():
    global_cfg = {"hooks": {"post": "echo done"}}
    policy = get_hook_policy({}, global_cfg)
    assert policy.post == ["echo done"]


def test_get_hook_policy_job_timeout_overrides():
    global_cfg = {"hooks": {"timeout": 10}}
    job_cfg = {"hooks": {"timeout": 5}}
    policy = get_hook_policy(job_cfg, global_cfg)
    assert policy.timeout == 5


# ---------------------------------------------------------------------------
# _run_hook
# ---------------------------------------------------------------------------

def test_run_hook_success():
    with patch("cronwatch.hooks.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        result = _run_hook("echo hi", 30, "pre")
    assert result is True


def test_run_hook_nonzero_returns_false():
    with patch("cronwatch.hooks.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stderr="oops")
        result = _run_hook("false", 30, "post")
    assert result is False


def test_run_hook_timeout_returns_false():
    import subprocess
    with patch("cronwatch.hooks.subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 5)):
        result = _run_hook("sleep 100", 5, "pre")
    assert result is False


def test_run_hook_exception_returns_false():
    with patch("cronwatch.hooks.subprocess.run", side_effect=OSError("no such file")):
        result = _run_hook("bad_cmd", 30, "on_failure")
    assert result is False


# ---------------------------------------------------------------------------
# run_hooks
# ---------------------------------------------------------------------------

def test_run_hooks_returns_list_of_results():
    with patch("cronwatch.hooks._run_hook", side_effect=[True, False, True]) as mock_hook:
        results = run_hooks(["cmd1", "cmd2", "cmd3"], 30, "post")
    assert results == [True, False, True]
    assert mock_hook.call_count == 3


def test_run_hooks_empty_list():
    results = run_hooks([], 30, "pre")
    assert results == []

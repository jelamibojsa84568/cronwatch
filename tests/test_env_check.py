"""Tests for cronwatch.env_check."""

import pytest
from cronwatch.env_check import (
    EnvCheckResult,
    check_all_jobs,
    check_job_env,
    format_env_check_report,
    get_required_commands,
    get_required_env_vars,
)


# ---------------------------------------------------------------------------
# get_required_commands
# ---------------------------------------------------------------------------

def test_get_required_commands_list():
    job = {"name": "j", "requires_commands": ["python3", "curl"]}
    assert get_required_commands(job) == ["python3", "curl"]


def test_get_required_commands_csv_string():
    job = {"name": "j", "requires_commands": "python3, curl"}
    assert get_required_commands(job) == ["python3", "curl"]


def test_get_required_commands_missing_key():
    assert get_required_commands({"name": "j"}) == []


# ---------------------------------------------------------------------------
# get_required_env_vars
# ---------------------------------------------------------------------------

def test_get_required_env_vars_list():
    job = {"name": "j", "requires_env": ["HOME", "PATH"]}
    assert get_required_env_vars(job) == ["HOME", "PATH"]


def test_get_required_env_vars_csv_string():
    job = {"name": "j", "requires_env": "HOME, PATH"}
    assert get_required_env_vars(job) == ["HOME", "PATH"]


# ---------------------------------------------------------------------------
# check_job_env
# ---------------------------------------------------------------------------

def test_check_job_env_all_ok():
    # 'echo' exists on every POSIX system; HOME is always in a real env
    job = {"name": "backup", "requires_commands": ["echo"], "requires_env": ["HOME"]}
    result = check_job_env(job)
    assert result.ok is True
    assert result.job_name == "backup"


def test_check_job_env_missing_command():
    job = {"name": "j", "requires_commands": ["__nonexistent_cmd_xyz__"]}
    result = check_job_env(job)
    assert result.ok is False
    assert "__nonexistent_cmd_xyz__" in result.missing_commands


def test_check_job_env_missing_env_var():
    job = {"name": "j", "requires_env": ["__MISSING_VAR_XYZ__"]}
    result = check_job_env(job, environ={})
    assert result.ok is False
    assert "__MISSING_VAR_XYZ__" in result.missing_env_vars


def test_check_job_env_custom_environ():
    job = {"name": "j", "requires_env": ["MY_TOKEN"]}
    result = check_job_env(job, environ={"MY_TOKEN": "secret"})
    assert result.ok is True


def test_env_check_result_repr_ok():
    r = EnvCheckResult(job_name="myjob")
    assert "ok=True" in repr(r)


def test_env_check_result_repr_fail():
    r = EnvCheckResult(job_name="myjob", missing_commands=["curl"])
    assert "missing_commands" in repr(r)
    assert "curl" in repr(r)


# ---------------------------------------------------------------------------
# check_all_jobs
# ---------------------------------------------------------------------------

def test_check_all_jobs_returns_one_per_job():
    jobs = [
        {"name": "a", "requires_commands": ["echo"]},
        {"name": "b", "requires_commands": ["echo"]},
    ]
    results = check_all_jobs(jobs)
    assert len(results) == 2
    assert all(r.ok for r in results)


# ---------------------------------------------------------------------------
# format_env_check_report
# ---------------------------------------------------------------------------

def test_format_env_check_report_ok_label():
    results = [EnvCheckResult(job_name="sync")]
    text = format_env_check_report(results)
    assert "[OK]" in text
    assert "sync" in text


def test_format_env_check_report_fail_label():
    results = [EnvCheckResult(job_name="deploy", missing_commands=["kubectl"])]
    text = format_env_check_report(results)
    assert "[FAIL]" in text
    assert "kubectl" in text


def test_format_env_check_report_header_shows_count():
    results = [EnvCheckResult(job_name="a"), EnvCheckResult(job_name="b")]
    text = format_env_check_report(results)
    assert "2 job(s)" in text

"""Tests for cronwatch.dependency."""

import json
import time
import pytest
from pathlib import Path

from cronwatch.dependency import (
    DependencyPolicy,
    get_dependency_policy,
    check_dependencies,
    DependencyCheckResult,
)


@pytest.fixture()
def history_dir(tmp_path):
    return str(tmp_path / "history")


def _write_entry(history_dir, job_name, exit_code=0, ts=None):
    d = Path(history_dir)
    d.mkdir(parents=True, exist_ok=True)
    safe = job_name.replace("/", "_").replace(" ", "_")
    path = d / f"{safe}.jsonl"
    entry = {"exit_code": exit_code, "timestamp": ts or time.time(), "job": job_name}
    with path.open("a") as f:
        f.write(json.dumps(entry) + "\n")


# --- get_dependency_policy ---

def test_get_dependency_policy_defaults_empty():
    policy = get_dependency_policy({}, {})
    assert policy.requires == []
    assert policy.max_age_minutes is None


def test_get_dependency_policy_list_shorthand():
    job = {"dependencies": ["job_a", "job_b"]}
    policy = get_dependency_policy(job, {})
    assert policy.requires == ["job_a", "job_b"]


def test_get_dependency_policy_dict_form():
    job = {"dependencies": {"requires": ["job_a"], "max_age_minutes": 30}}
    policy = get_dependency_policy(job, {})
    assert policy.requires == ["job_a"]
    assert policy.max_age_minutes == 30


def test_get_dependency_policy_global_fallback():
    config = {"defaults": {"dependencies": {"requires": ["setup"]}}}
    policy = get_dependency_policy({}, config)
    assert "setup" in policy.requires


def test_get_dependency_policy_job_overrides_global():
    config = {"defaults": {"dependencies": {"requires": ["setup"]}}}
    job = {"dependencies": ["other_job"]}
    policy = get_dependency_policy(job, config)
    assert policy.requires == ["other_job"]


def test_get_dependency_policy_csv_string():
    job = {"dependencies": {"requires": "job_a, job_b"}}
    policy = get_dependency_policy(job, {})
    assert policy.requires == ["job_a", "job_b"]


# --- check_dependencies ---

def test_check_dependencies_no_requires_satisfied(history_dir):
    policy = DependencyPolicy(requires=[])
    result = check_dependencies(policy, history_dir)
    assert result.satisfied is True


def test_check_dependencies_satisfied_when_success_recorded(history_dir):
    _write_entry(history_dir, "job_a", exit_code=0)
    policy = DependencyPolicy(requires=["job_a"])
    result = check_dependencies(policy, history_dir)
    assert result.satisfied is True


def test_check_dependencies_fails_when_no_history(history_dir):
    policy = DependencyPolicy(requires=["missing_job"])
    result = check_dependencies(policy, history_dir)
    assert result.satisfied is False
    assert result.blocking_job == "missing_job"
    assert "no successful run" in result.reason


def test_check_dependencies_fails_when_only_failures(history_dir):
    _write_entry(history_dir, "job_b", exit_code=1)
    policy = DependencyPolicy(requires=["job_b"])
    result = check_dependencies(policy, history_dir)
    assert result.satisfied is False
    assert result.blocking_job == "job_b"


def test_check_dependencies_max_age_satisfied(history_dir):
    _write_entry(history_dir, "job_c", exit_code=0, ts=time.time() - 60)
    policy = DependencyPolicy(requires=["job_c"], max_age_minutes=5)
    result = check_dependencies(policy, history_dir)
    assert result.satisfied is False
    assert "min ago" in result.reason


def test_check_dependencies_max_age_recent_passes(history_dir):
    _write_entry(history_dir, "job_d", exit_code=0, ts=time.time() - 30)
    policy = DependencyPolicy(requires=["job_d"], max_age_minutes=5)
    result = check_dependencies(policy, history_dir)
    assert result.satisfied is True

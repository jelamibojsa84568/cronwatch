"""Tests for cronwatch.rate_limit."""

import json
import time
from pathlib import Path

import pytest

from cronwatch.rate_limit import (
    RateLimitPolicy,
    check_rate_limit,
    get_rate_limit_policy,
    record_run,
)


@pytest.fixture
def state_dir(tmp_path):
    return str(tmp_path)


# --- get_rate_limit_policy ---

def test_get_rate_limit_policy_defaults():
    policy = get_rate_limit_policy({}, {})
    assert policy.enabled is False
    assert policy.min_interval == 0


def test_get_rate_limit_policy_global_int():
    policy = get_rate_limit_policy({}, {"rate_limit": 300})
    assert policy.enabled is True
    assert policy.min_interval == 300


def test_get_rate_limit_policy_job_overrides_global():
    policy = get_rate_limit_policy(
        {"rate_limit": 60},
        {"rate_limit": 300},
    )
    assert policy.min_interval == 60


def test_get_rate_limit_policy_dict_form():
    policy = get_rate_limit_policy({"rate_limit": {"min_interval": 120}}, {})
    assert policy.enabled is True
    assert policy.min_interval == 120


# --- RateLimitPolicy ---

def test_rate_limit_policy_is_limited_true():
    p = RateLimitPolicy(enabled=True, min_interval=60)
    assert p.is_limited() is True


def test_rate_limit_policy_is_limited_false_when_disabled():
    p = RateLimitPolicy(enabled=False, min_interval=60)
    assert p.is_limited() is False


def test_rate_limit_policy_repr_disabled():
    p = RateLimitPolicy(enabled=False, min_interval=0)
    assert "disabled" in repr(p)


def test_rate_limit_policy_repr_shows_interval():
    p = RateLimitPolicy(enabled=True, min_interval=90)
    assert "90s" in repr(p)


# --- record_run / check_rate_limit ---

def test_check_rate_limit_no_state_returns_false(state_dir):
    policy = RateLimitPolicy(enabled=True, min_interval=300)
    limited, remaining = check_rate_limit(policy, state_dir, "backup")
    assert limited is False
    assert remaining == 0.0


def test_check_rate_limit_disabled_always_false(state_dir):
    policy = RateLimitPolicy(enabled=False, min_interval=300)
    record_run(state_dir, "backup")
    limited, _ = check_rate_limit(policy, state_dir, "backup")
    assert limited is False


def test_record_run_creates_state_file(state_dir):
    record_run(state_dir, "my job")
    files = list(Path(state_dir).glob("ratelimit_*.json"))
    assert len(files) == 1


def test_check_rate_limit_true_immediately_after_run(state_dir):
    policy = RateLimitPolicy(enabled=True, min_interval=600)
    record_run(state_dir, "nightly")
    limited, remaining = check_rate_limit(policy, state_dir, "nightly")
    assert limited is True
    assert remaining > 0


def test_check_rate_limit_false_after_interval_elapsed(state_dir):
    policy = RateLimitPolicy(enabled=True, min_interval=1)
    record_run(state_dir, "fast")
    time.sleep(1.05)
    limited, remaining = check_rate_limit(policy, state_dir, "fast")
    assert limited is False
    assert remaining == 0.0


def test_record_run_stores_timestamp(state_dir):
    before = time.time()
    record_run(state_dir, "check")
    after = time.time()
    files = list(Path(state_dir).glob("ratelimit_*.json"))
    data = json.loads(files[0].read_text())
    assert before <= data["last_run"] <= after

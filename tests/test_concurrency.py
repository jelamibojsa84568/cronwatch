"""Tests for cronwatch.concurrency."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from cronwatch.concurrency import (
    ConcurrencyPolicy,
    acquire_slot,
    get_concurrency_policy,
    release_slot,
    _state_path,
    _load_active,
)


@pytest.fixture()
def state_dir(tmp_path: Path) -> Path:
    return tmp_path / "concurrency"


@pytest.fixture()
def policy(state_dir: Path) -> ConcurrencyPolicy:
    return ConcurrencyPolicy(max_instances=2, state_dir=str(state_dir))


# ---------------------------------------------------------------------------
# get_concurrency_policy
# ---------------------------------------------------------------------------

def test_get_concurrency_policy_defaults():
    pol = get_concurrency_policy({}, {})
    assert pol.max_instances == 1


def test_get_concurrency_policy_global_int():
    pol = get_concurrency_policy({}, {"concurrency": 3})
    assert pol.max_instances == 3


def test_get_concurrency_policy_job_overrides_global():
    pol = get_concurrency_policy(
        {"concurrency": {"max_instances": 5}},
        {"concurrency": {"max_instances": 2}},
    )
    assert pol.max_instances == 5


def test_get_concurrency_policy_job_int_shorthand():
    pol = get_concurrency_policy({"concurrency": 4}, {})
    assert pol.max_instances == 4


# ---------------------------------------------------------------------------
# ConcurrencyPolicy.is_limited
# ---------------------------------------------------------------------------

def test_is_limited_true_when_positive():
    assert ConcurrencyPolicy(max_instances=1).is_limited() is True


def test_is_limited_false_when_zero():
    assert ConcurrencyPolicy(max_instances=0).is_limited() is False


# ---------------------------------------------------------------------------
# acquire_slot / release_slot
# ---------------------------------------------------------------------------

def test_acquire_slot_succeeds_when_under_limit(policy):
    assert acquire_slot(policy, "my-job") is True


def test_acquire_slot_fails_when_at_limit(policy):
    # Fill all slots with the current PID (fake two entries)
    path = _state_path(policy, "my-job")
    path.parent.mkdir(parents=True, exist_ok=True)
    # Use two fake-but-alive PIDs: current PID listed twice is fine for the
    # count check; we just need len(active) >= max_instances.
    pid = os.getpid()
    path.write_text(json.dumps({"pids": [pid, pid]}))
    assert acquire_slot(policy, "my-job") is False


def test_acquire_slot_unlimited_always_succeeds(state_dir):
    pol = ConcurrencyPolicy(max_instances=0, state_dir=str(state_dir))
    for _ in range(10):
        assert acquire_slot(pol, "unlimited-job") is True


def test_release_slot_removes_current_pid(policy):
    acquire_slot(policy, "release-job")
    release_slot(policy, "release-job")
    path = _state_path(policy, "release-job")
    active = _load_active(path)
    assert os.getpid() not in active


def test_acquire_prunes_dead_pids(policy):
    # Write a dead PID so the slot appears taken, but should be pruned.
    path = _state_path(policy, "prune-job")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"pids": [999999999]}))
    # After pruning the dead PID, slot should be available.
    assert acquire_slot(policy, "prune-job") is True

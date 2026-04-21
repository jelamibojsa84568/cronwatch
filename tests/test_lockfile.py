"""Tests for cronwatch.lockfile."""

import os
import time
import pytest

from cronwatch.lockfile import (
    LockPolicy,
    get_lock_policy,
    acquire_lock,
    release_lock,
    LockAcquireError,
)


@pytest.fixture
def lock_dir(tmp_path):
    return str(tmp_path / "locks")


@pytest.fixture
def policy(lock_dir):
    return LockPolicy(enabled=True, lock_dir=lock_dir, stale_after=0)


# --- get_lock_policy ---

def test_get_lock_policy_defaults():
    pol = get_lock_policy({}, {})
    assert pol.enabled is False
    assert pol.stale_after == 0


def test_get_lock_policy_global_config():
    config = {"lockfile": {"enabled": True, "stale_after": 300}}
    pol = get_lock_policy(config, {})
    assert pol.enabled is True
    assert pol.stale_after == 300


def test_get_lock_policy_job_overrides_global():
    config = {"lockfile": {"enabled": False, "stale_after": 60}}
    job = {"lockfile": {"enabled": True, "stale_after": 120}}
    pol = get_lock_policy(config, job)
    assert pol.enabled is True
    assert pol.stale_after == 120


def test_get_lock_policy_job_scalar_bool():
    config = {"lockfile": {"enabled": False}}
    job = {"lockfile": True}
    pol = get_lock_policy(config, job)
    assert pol.enabled is True


def test_get_lock_policy_custom_lock_dir():
    config = {"lockfile": {"enabled": True, "lock_dir": "/var/run/cw"}}
    pol = get_lock_policy(config, {})
    assert pol.lock_dir == "/var/run/cw"


# --- acquire_lock / release_lock ---

def test_acquire_lock_creates_file(policy, lock_dir):
    path = acquire_lock(policy, "backup")
    assert os.path.exists(path)


def test_acquire_lock_writes_pid(policy):
    path = acquire_lock(policy, "backup")
    with open(path) as fh:
        assert fh.read().strip() == str(os.getpid())


def test_acquire_lock_raises_when_held(policy):
    acquire_lock(policy, "backup")
    with pytest.raises(LockAcquireError, match="backup"):
        acquire_lock(policy, "backup")


def test_release_lock_removes_file(policy):
    acquire_lock(policy, "cleanup")
    release_lock(policy, "cleanup")
    lock_dir = policy.lock_dir
    path = os.path.join(lock_dir, "cleanup.lock")
    assert not os.path.exists(path)


def test_release_lock_no_error_when_missing(policy):
    # Should not raise even if lock was never acquired
    release_lock(policy, "nonexistent")


def test_acquire_lock_removes_stale_lock(lock_dir):
    stale_policy = LockPolicy(enabled=True, lock_dir=lock_dir, stale_after=1)
    path = acquire_lock(stale_policy, "stale_job")
    # Backdate the file modification time by 5 seconds
    old_time = time.time() - 5
    os.utime(path, (old_time, old_time))
    # Should succeed without raising
    path2 = acquire_lock(stale_policy, "stale_job")
    assert os.path.exists(path2)


def test_lock_sanitizes_job_name(policy, lock_dir):
    acquire_lock(policy, "my job/with spaces")
    expected = os.path.join(lock_dir, "my_job_with_spaces.lock")
    assert os.path.exists(expected)

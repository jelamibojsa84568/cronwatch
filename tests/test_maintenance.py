"""Tests for cronwatch.maintenance."""

from datetime import datetime, time

import pytest

from cronwatch.maintenance import (
    MaintenanceWindow,
    _parse_days,
    _parse_time,
    is_in_maintenance,
    parse_maintenance_windows,
)


# ---------------------------------------------------------------------------
# _parse_time
# ---------------------------------------------------------------------------

def test_parse_time_basic():
    assert _parse_time("02:30") == time(2, 30)


def test_parse_time_single_digit_hour():
    assert _parse_time("9:05") == time(9, 5)


def test_parse_time_invalid_raises():
    with pytest.raises(ValueError, match="Invalid time"):
        _parse_time("25:00")


# ---------------------------------------------------------------------------
# _parse_days
# ---------------------------------------------------------------------------

def test_parse_days_none_returns_none():
    assert _parse_days(None) is None


def test_parse_days_name_list():
    assert _parse_days(["mon", "fri"]) == [0, 4]


def test_parse_days_csv_string():
    assert _parse_days("tue,wed") == [1, 2]


def test_parse_days_invalid_raises():
    with pytest.raises(ValueError, match="Unknown day"):
        _parse_days(["funday"])


# ---------------------------------------------------------------------------
# MaintenanceWindow.is_active
# ---------------------------------------------------------------------------

def _dt(hour, minute, weekday=0):
    """Build a datetime with given time; weekday 0=Mon."""
    # 2024-01-01 is a Monday
    base = datetime(2024, 1, 1 + weekday, hour, minute)
    return base


def test_window_active_within_range():
    w = MaintenanceWindow(time(2, 0), time(4, 0))
    assert w.is_active(_dt(3, 0)) is True


def test_window_inactive_outside_range():
    w = MaintenanceWindow(time(2, 0), time(4, 0))
    assert w.is_active(_dt(5, 0)) is False


def test_window_overnight_active():
    w = MaintenanceWindow(time(23, 0), time(1, 0))
    assert w.is_active(_dt(0, 30)) is True


def test_window_overnight_inactive():
    w = MaintenanceWindow(time(23, 0), time(1, 0))
    assert w.is_active(_dt(12, 0)) is False


def test_window_day_filter_active():
    w = MaintenanceWindow(time(2, 0), time(4, 0), days=[0])  # Monday only
    assert w.is_active(_dt(3, 0, weekday=0)) is True


def test_window_day_filter_inactive_wrong_day():
    w = MaintenanceWindow(time(2, 0), time(4, 0), days=[0])  # Monday only
    assert w.is_active(_dt(3, 0, weekday=2)) is False  # Wednesday


# ---------------------------------------------------------------------------
# parse_maintenance_windows
# ---------------------------------------------------------------------------

def test_parse_maintenance_windows_empty():
    assert parse_maintenance_windows([]) == []


def test_parse_maintenance_windows_single_dict():
    raw = {"start": "02:00", "end": "04:00"}
    windows = parse_maintenance_windows(raw)
    assert len(windows) == 1
    assert windows[0].start == time(2, 0)


def test_parse_maintenance_windows_list():
    raw = [
        {"start": "01:00", "end": "02:00"},
        {"start": "23:00", "end": "23:30", "days": "sat,sun"},
    ]
    windows = parse_maintenance_windows(raw)
    assert len(windows) == 2
    assert windows[1].days == [5, 6]


# ---------------------------------------------------------------------------
# is_in_maintenance
# ---------------------------------------------------------------------------

def test_is_in_maintenance_no_windows():
    assert is_in_maintenance({}, {}) is False


def test_is_in_maintenance_global_window_active():
    config = {"maintenance": [{"start": "02:00", "end": "04:00"}]}
    now = _dt(3, 0)
    assert is_in_maintenance({}, config, now=now) is True


def test_is_in_maintenance_job_window_active():
    job = {"name": "backup", "maintenance": [{"start": "05:00", "end": "06:00"}]}
    now = _dt(5, 30)
    assert is_in_maintenance(job, {}, now=now) is True


def test_is_in_maintenance_outside_all_windows():
    config = {"maintenance": [{"start": "02:00", "end": "04:00"}]}
    now = _dt(10, 0)
    assert is_in_maintenance({}, config, now=now) is False

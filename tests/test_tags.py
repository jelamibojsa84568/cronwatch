"""Tests for cronwatch.tags module."""
import pytest
from cronwatch.tags import get_job_tags, filter_jobs_by_tags, list_all_tags


JOBS = [
    {"name": "backup", "schedule": "0 2 * * *", "command": "backup.sh", "tags": ["nightly", "critical"]},
    {"name": "cleanup", "schedule": "0 3 * * *", "command": "clean.sh", "tags": ["nightly", "safe"]},
    {"name": "report", "schedule": "0 8 * * 1", "command": "report.sh", "tags": ["weekly"]},
    {"name": "ping", "schedule": "* * * * *", "command": "ping.sh"},
]


def test_get_job_tags_list():
    assert get_job_tags(JOBS[0]) == ["nightly", "critical"]


def test_get_job_tags_missing_returns_empty():
    assert get_job_tags(JOBS[3]) == []


def test_get_job_tags_string_csv():
    job = {"name": "x", "tags": "alpha, beta, gamma"}
    assert get_job_tags(job) == ["alpha", "beta", "gamma"]


def test_filter_jobs_by_include_single_tag():
    result = filter_jobs_by_tags(JOBS, include=["nightly"])
    names = [j["name"] for j in result]
    assert names == ["backup", "cleanup"]


def test_filter_jobs_by_include_multiple_tags():
    result = filter_jobs_by_tags(JOBS, include=["nightly", "critical"])
    names = [j["name"] for j in result]
    assert names == ["backup"]


def test_filter_jobs_by_exclude():
    result = filter_jobs_by_tags(JOBS, exclude=["critical"])
    names = [j["name"] for j in result]
    assert "backup" not in names
    assert "cleanup" in names


def test_filter_jobs_include_and_exclude():
    result = filter_jobs_by_tags(JOBS, include=["nightly"], exclude=["safe"])
    names = [j["name"] for j in result]
    assert names == ["backup"]


def test_filter_jobs_no_filters_returns_all():
    result = filter_jobs_by_tags(JOBS)
    assert result == JOBS


def test_list_all_tags_sorted_unique():
    tags = list_all_tags(JOBS)
    assert tags == ["critical", "nightly", "safe", "weekly"]


def test_list_all_tags_empty_jobs():
    assert list_all_tags([]) == []

"""
tests/test_labels.py

Tests for cronwatch.labels.
"""
import pytest
from cronwatch.labels import (
    get_job_labels,
    filter_jobs_by_labels,
    list_all_label_keys,
    build_label_index,
)


# ---------------------------------------------------------------------------
# get_job_labels
# ---------------------------------------------------------------------------

def test_get_job_labels_dict():
    job = {"name": "j", "labels": {"env": "prod", "team": "ops"}}
    assert get_job_labels(job) == {"env": "prod", "team": "ops"}


def test_get_job_labels_csv_string():
    job = {"name": "j", "labels": "env=prod, team=ops"}
    assert get_job_labels(job) == {"env": "prod", "team": "ops"}


def test_get_job_labels_missing_returns_empty():
    assert get_job_labels({"name": "j"}) == {}


def test_get_job_labels_csv_ignores_malformed_pairs():
    job = {"name": "j", "labels": "env=prod, badpair, team=ops"}
    result = get_job_labels(job)
    assert result["env"] == "prod"
    assert result["team"] == "ops"
    assert "badpair" not in result


def test_get_job_labels_coerces_values_to_str():
    job = {"name": "j", "labels": {"priority": 1}}
    assert get_job_labels(job) == {"priority": "1"}


# ---------------------------------------------------------------------------
# filter_jobs_by_labels
# ---------------------------------------------------------------------------

def _jobs():
    return [
        {"name": "a", "labels": {"env": "prod", "team": "ops"}},
        {"name": "b", "labels": {"env": "staging", "team": "ops"}},
        {"name": "c", "labels": {"env": "prod", "team": "dev"}},
        {"name": "d"},
    ]


def test_filter_jobs_by_labels_single_pair():
    result = filter_jobs_by_labels(_jobs(), {"env": "prod"})
    names = [j["name"] for j in result]
    assert names == ["a", "c"]


def test_filter_jobs_by_labels_multiple_pairs():
    result = filter_jobs_by_labels(_jobs(), {"env": "prod", "team": "ops"})
    names = [j["name"] for j in result]
    assert names == ["a"]


def test_filter_jobs_by_labels_no_match_returns_empty():
    result = filter_jobs_by_labels(_jobs(), {"env": "canary"})
    assert result == []


def test_filter_jobs_by_labels_none_match_returns_all():
    result = filter_jobs_by_labels(_jobs(), None)
    assert len(result) == 4


# ---------------------------------------------------------------------------
# list_all_label_keys
# ---------------------------------------------------------------------------

def test_list_all_label_keys_sorted():
    keys = list_all_label_keys(_jobs())
    assert keys == ["env", "team"]


def test_list_all_label_keys_empty_when_no_labels():
    assert list_all_label_keys([{"name": "x"}]) == []


# ---------------------------------------------------------------------------
# build_label_index
# ---------------------------------------------------------------------------

def test_build_label_index_structure():
    index = build_label_index(_jobs())
    assert set(index.keys()) == {"env", "team"}
    assert sorted(index["env"]["prod"]) == ["a", "c"]
    assert sorted(index["team"]["ops"]) == ["a", "b"]


def test_build_label_index_empty_jobs():
    assert build_label_index([]) == {}

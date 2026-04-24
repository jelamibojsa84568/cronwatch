"""Tests for cronwatch.metrics."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from cronwatch.metrics import (
    compute_metrics,
    format_metrics_text,
    load_metrics,
    save_metrics,
)


@pytest.fixture()
def history_dir(tmp_path: Path) -> str:
    return str(tmp_path / "history")


@pytest.fixture()
def metrics_dir(tmp_path: Path) -> str:
    return str(tmp_path / "metrics")


def _write_entry(history_dir: str, job_name: str, exit_code: int, duration: float) -> None:
    safe = job_name.replace("/", "_").replace(" ", "_")
    p = Path(history_dir) / f"{safe}.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    entry = {"job": job_name, "exit_code": exit_code, "duration": duration, "timestamp": time.time()}
    with p.open("a") as fh:
        fh.write(json.dumps(entry) + "\n")


def test_compute_metrics_no_history(history_dir: str) -> None:
    m = compute_metrics("missing_job", history_dir)
    assert m["runs"] == 0
    assert m["success_rate"] is None
    assert m["avg_duration"] is None


def test_compute_metrics_all_successes(history_dir: str) -> None:
    for i in range(5):
        _write_entry(history_dir, "backup", 0, float(i + 1))
    m = compute_metrics("backup", history_dir)
    assert m["runs"] == 5
    assert m["successes"] == 5
    assert m["failures"] == 0
    assert m["success_rate"] == 100.0


def test_compute_metrics_mixed_results(history_dir: str) -> None:
    _write_entry(history_dir, "sync", 0, 1.0)
    _write_entry(history_dir, "sync", 1, 2.0)
    _write_entry(history_dir, "sync", 0, 3.0)
    m = compute_metrics("sync", history_dir)
    assert m["runs"] == 3
    assert m["successes"] == 2
    assert m["failures"] == 1
    assert m["success_rate"] == pytest.approx(66.7)


def test_compute_metrics_duration_stats(history_dir: str) -> None:
    for d in [2.0, 4.0, 6.0]:
        _write_entry(history_dir, "etl", 0, d)
    m = compute_metrics("etl", history_dir)
    assert m["avg_duration"] == pytest.approx(4.0)
    assert m["min_duration"] == pytest.approx(2.0)
    assert m["max_duration"] == pytest.approx(6.0)


def test_compute_metrics_last_status_failure(history_dir: str) -> None:
    _write_entry(history_dir, "report", 0, 1.0)
    _write_entry(history_dir, "report", 2, 1.0)
    m = compute_metrics("report", history_dir)
    assert m["last_status"] == "failure"


def test_save_and_load_metrics(history_dir: str, metrics_dir: str) -> None:
    _write_entry(history_dir, "cleanup", 0, 0.5)
    m = compute_metrics("cleanup", history_dir)
    save_metrics(m, metrics_dir)
    loaded = load_metrics("cleanup", metrics_dir)
    assert loaded is not None
    assert loaded["job"] == "cleanup"
    assert loaded["runs"] == 1
    assert "computed_at" in loaded


def test_load_metrics_returns_none_when_missing(metrics_dir: str) -> None:
    result = load_metrics("nonexistent", metrics_dir)
    assert result is None


def test_format_metrics_text_no_runs(history_dir: str) -> None:
    m = compute_metrics("ghost", history_dir)
    text = format_metrics_text(m)
    assert "No history" in text


def test_format_metrics_text_with_runs(history_dir: str) -> None:
    _write_entry(history_dir, "ping", 0, 0.1)
    m = compute_metrics("ping", history_dir)
    text = format_metrics_text(m)
    assert "ping" in text
    assert "100.0%" in text
    assert "Avg duration" in text

"""
cronwatch/labels.py

Support for arbitrary key-value labels on jobs, enabling fine-grained
filtering, grouping, and reporting beyond simple tags.
"""
from typing import Any, Dict, List, Optional


def get_job_labels(job: Dict[str, Any]) -> Dict[str, str]:
    """Return the labels dict for a job.

    Accepts either a proper dict or a CSV string of key=value pairs.
    Returns an empty dict if no labels are defined.
    """
    raw = job.get("labels", {})
    if isinstance(raw, str):
        result: Dict[str, str] = {}
        for pair in raw.split(","):
            pair = pair.strip()
            if "=" in pair:
                k, v = pair.split("=", 1)
                result[k.strip()] = v.strip()
        return result
    if isinstance(raw, dict):
        return {str(k): str(v) for k, v in raw.items()}
    return {}


def filter_jobs_by_labels(
    jobs: List[Dict[str, Any]],
    match: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """Return jobs whose labels contain ALL key-value pairs in *match*."""
    if not match:
        return list(jobs)
    return [
        job for job in jobs
        if all(get_job_labels(job).get(k) == v for k, v in match.items())
    ]


def list_all_label_keys(jobs: List[Dict[str, Any]]) -> List[str]:
    """Return a sorted, deduplicated list of every label key used across jobs."""
    keys: set = set()
    for job in jobs:
        keys.update(get_job_labels(job).keys())
    return sorted(keys)


def build_label_index(
    jobs: List[Dict[str, Any]],
) -> Dict[str, Dict[str, List[str]]]:
    """Build a nested index: {label_key: {label_value: [job_name, ...]}}."""
    index: Dict[str, Dict[str, List[str]]] = {}
    for job in jobs:
        name = job.get("name", "<unnamed>")
        for k, v in get_job_labels(job).items():
            index.setdefault(k, {}).setdefault(v, []).append(name)
    return index

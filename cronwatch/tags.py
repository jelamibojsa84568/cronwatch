"""Tag-based filtering for cron jobs."""
from typing import List, Dict, Any


def get_job_tags(job: Dict[str, Any]) -> List[str]:
    """Return the list of tags for a job, defaulting to empty list."""
    raw = job.get("tags", [])
    if isinstance(raw, str):
        return [t.strip() for t in raw.split(",") if t.strip()]
    return [str(t) for t in raw]


def filter_jobs_by_tags(
    jobs: List[Dict[str, Any]],
    include: List[str] = None,
    exclude: List[str] = None,
) -> List[Dict[str, Any]]:
    """Filter jobs by tag inclusion/exclusion.

    Args:
        jobs: List of job dicts.
        include: Only return jobs that have ALL of these tags.
        exclude: Omit jobs that have ANY of these tags.

    Returns:
        Filtered list of jobs.
    """
    result = []
    for job in jobs:
        job_tags = set(get_job_tags(job))
        if include and not set(include).issubset(job_tags):
            continue
        if exclude and job_tags.intersection(exclude):
            continue
        result.append(job)
    return result


def list_all_tags(jobs: List[Dict[str, Any]]) -> List[str]:
    """Return a sorted list of unique tags across all jobs."""
    tags: set = set()
    for job in jobs:
        tags.update(get_job_tags(job))
    return sorted(tags)

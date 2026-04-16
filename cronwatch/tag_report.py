"""Per-tag summary report utilities."""
from typing import Dict, List, Any
from cronwatch.tags import get_job_tags, list_all_tags
from cronwatch.history import get_history


def build_tag_report(
    jobs: List[Dict[str, Any]],
    history_dir: str,
    limit: int = 50,
) -> Dict[str, Dict[str, int]]:
    """Build a summary of run/fail counts grouped by tag.

    Returns:
        Dict mapping tag -> {"runs": int, "failures": int}
    """
    tags = list_all_tags(jobs)
    summary: Dict[str, Dict[str, int]] = {t: {"runs": 0, "failures": 0} for t in tags}

    for job in jobs:
        job_tags = get_job_tags(job)
        if not job_tags:
            continue
        entries = get_history(job["name"], history_dir=history_dir, limit=limit)
        runs = len(entries)
        failures = sum(1 for e in entries if not e.get("success", True))
        for tag in job_tags:
            summary[tag]["runs"] += runs
            summary[tag]["failures"] += failures

    return summary


def format_tag_report(summary: Dict[str, Dict[str, int]]) -> str:
    """Render the tag report as a human-readable string."""
    if not summary:
        return "No tagged jobs found."
    lines = ["Tag Report", "=" * 40]
    for tag in sorted(summary):
        data = summary[tag]
        runs = data["runs"]
        failures = data["failures"]
        pct = (failures / runs * 100) if runs else 0.0
        lines.append(f"{tag:<20} runs={runs:>4}  failures={failures:>4}  ({pct:.1f}%)")
    return "\n".join(lines)

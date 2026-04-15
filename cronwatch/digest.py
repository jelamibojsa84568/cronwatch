"""Daily digest report builder for cronwatch."""

from datetime import datetime, timezone
from typing import List, Dict, Any

from cronwatch.history import get_history


def _format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes}m {secs}s"


def build_digest(jobs: List[str], history_dir: str, since_hours: int = 24) -> Dict[str, Any]:
    """Aggregate job run stats over the last `since_hours` hours."""
    cutoff = datetime.now(timezone.utc).timestamp() - since_hours * 3600
    report: Dict[str, Any] = {}

    for job_name in jobs:
        entries = [
            e for e in get_history(job_name, history_dir)
            if e.get("timestamp", 0) >= cutoff
        ]
        total = len(entries)
        failures = [e for e in entries if not e.get("success", True)]
        durations = [e["duration"] for e in entries if "duration" in e]

        report[job_name] = {
            "total_runs": total,
            "failures": len(failures),
            "success_rate": round((total - len(failures)) / total * 100, 1) if total else None,
            "avg_duration": _format_duration(sum(durations) / len(durations)) if durations else None,
            "last_exit_code": entries[-1].get("exit_code") if entries else None,
        }
    return report


def format_digest_text(report: Dict[str, Any], since_hours: int = 24) -> str:
    """Render the digest report as a plain-text string."""
    lines = [
        f"cronwatch digest — last {since_hours}h",
        "=" * 40,
    ]
    for job_name, stats in sorted(report.items()):
        lines.append(f"\nJob: {job_name}")
        lines.append(f"  Runs     : {stats['total_runs']}")
        lines.append(f"  Failures : {stats['failures']}")
        sr = stats['success_rate']
        lines.append(f"  Success% : {sr}%" if sr is not None else "  Success% : n/a")
        dur = stats['avg_duration']
        lines.append(f"  Avg dur  : {dur}" if dur else "  Avg dur  : n/a")
        ec = stats['last_exit_code']
        lines.append(f"  Last exit: {ec}" if ec is not None else "  Last exit: n/a")
    lines.append("\n" + "=" * 40)
    return "\n".join(lines)

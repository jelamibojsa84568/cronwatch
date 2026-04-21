"""Job dependency checking — ensure prerequisite jobs have run successfully."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from cronwatch.history import get_history


@dataclass
class DependencyPolicy:
    requires: List[str] = field(default_factory=list)
    max_age_minutes: Optional[int] = None  # None = any successful run counts


def get_dependency_policy(job: dict, config: dict) -> DependencyPolicy:
    """Build a DependencyPolicy for *job*, merging global defaults."""
    global_deps = config.get("defaults", {}).get("dependencies", {})
    job_deps = job.get("dependencies", {})

    # Support plain list shorthand: dependencies: [job_a, job_b]
    if isinstance(job_deps, list):
        job_deps = {"requires": job_deps}
    if isinstance(global_deps, list):
        global_deps = {"requires": global_deps}

    requires = job_deps.get("requires", global_deps.get("requires", []))
    if isinstance(requires, str):
        requires = [r.strip() for r in requires.split(",") if r.strip()]

    max_age = job_deps.get(
        "max_age_minutes", global_deps.get("max_age_minutes", None)
    )
    if max_age is not None:
        max_age = int(max_age)

    return DependencyPolicy(requires=requires, max_age_minutes=max_age)


@dataclass
class DependencyCheckResult:
    satisfied: bool
    blocking_job: Optional[str] = None
    reason: Optional[str] = None

    def __repr__(self) -> str:  # pragma: no cover
        if self.satisfied:
            return "DependencyCheckResult(satisfied=True)"
        return f"DependencyCheckResult(satisfied=False, blocking={self.blocking_job!r}, reason={self.reason!r})"


def check_dependencies(
    policy: DependencyPolicy, history_dir: str
) -> DependencyCheckResult:
    """Return a DependencyCheckResult indicating whether all required jobs
    have a recent successful run in the history store."""
    import time

    for required_job in policy.requires:
        entries = get_history(required_job, history_dir=history_dir)
        # Filter to successful runs only
        successes = [e for e in entries if e.get("exit_code", 1) == 0]
        if not successes:
            return DependencyCheckResult(
                satisfied=False,
                blocking_job=required_job,
                reason="no successful run recorded",
            )
        if policy.max_age_minutes is not None:
            latest_ts = max(e.get("timestamp", 0) for e in successes)
            age_minutes = (time.time() - latest_ts) / 60.0
            if age_minutes > policy.max_age_minutes:
                return DependencyCheckResult(
                    satisfied=False,
                    blocking_job=required_job,
                    reason=(
                        f"last success was {age_minutes:.1f} min ago "
                        f"(max {policy.max_age_minutes} min)"
                    ),
                )
    return DependencyCheckResult(satisfied=True)

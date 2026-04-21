"""Environment and dependency checks for cronwatch jobs."""

import shutil
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class EnvCheckResult:
    job_name: str
    missing_commands: List[str] = field(default_factory=list)
    missing_env_vars: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.missing_commands and not self.missing_env_vars

    def __repr__(self) -> str:
        if self.ok:
            return f"<EnvCheckResult job={self.job_name!r} ok=True>"
        parts = []
        if self.missing_commands:
            parts.append(f"missing_commands={self.missing_commands}")
        if self.missing_env_vars:
            parts.append(f"missing_env_vars={self.missing_env_vars}")
        return f"<EnvCheckResult job={self.job_name!r} " + " ".join(parts) + ">"


def get_required_commands(job: dict) -> List[str]:
    """Return list of commands the job declares it requires."""
    value = job.get("requires_commands", [])
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return list(value)


def get_required_env_vars(job: dict) -> List[str]:
    """Return list of env vars the job declares it requires."""
    value = job.get("requires_env", [])
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return list(value)


def check_job_env(job: dict, environ: Optional[dict] = None) -> EnvCheckResult:
    """Check that all declared commands and env vars are available."""
    import os

    env = environ if environ is not None else os.environ
    name = job.get("name", "<unknown>")
    result = EnvCheckResult(job_name=name)

    for cmd in get_required_commands(job):
        if shutil.which(cmd) is None:
            result.missing_commands.append(cmd)

    for var in get_required_env_vars(job):
        if var not in env:
            result.missing_env_vars.append(var)

    return result


def check_all_jobs(jobs: List[dict], environ: Optional[dict] = None) -> List[EnvCheckResult]:
    """Run env checks for every job in the list."""
    return [check_job_env(job, environ=environ) for job in jobs]


def format_env_check_report(results: List[EnvCheckResult]) -> str:
    """Return a human-readable summary of env check results."""
    lines = []
    for r in results:
        if r.ok:
            lines.append(f"  [OK]   {r.job_name}")
        else:
            lines.append(f"  [FAIL] {r.job_name}")
            for cmd in r.missing_commands:
                lines.append(f"           missing command: {cmd}")
            for var in r.missing_env_vars:
                lines.append(f"           missing env var: {var}")
    header = f"Environment check — {len(results)} job(s)\n"
    return header + "\n".join(lines)

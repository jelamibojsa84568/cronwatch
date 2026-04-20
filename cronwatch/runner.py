"""Execute cron job commands and capture results."""

import subprocess
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class JobResult:
    """Holds the outcome of a single cron job execution."""

    job_name: str
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    started_at: float = field(default_factory=time.time)

    @property
    def success(self) -> bool:
        return self.exit_code == 0

    def __repr__(self) -> str:
        status = "OK" if self.success else f"FAILED(exit={self.exit_code})"
        return (
            f"<JobResult job={self.job_name!r} status={status} "
            f"duration={self.duration_seconds:.2f}s>"
        )


def run_job(
    job_name: str,
    command: str,
    timeout: Optional[int] = None,
    shell: bool = True,
) -> JobResult:
    """Run *command* as a subprocess and return a :class:`JobResult`.

    Args:
        job_name: Human-readable label for this job (used in logs / alerts).
        command:  Shell command string to execute.
        timeout:  Optional maximum runtime in seconds.  If the process exceeds
                  this limit it is killed and the exit code is set to -1.
        shell:    Pass the command to the system shell (default ``True``).

    Returns:
        A populated :class:`JobResult` instance.
    """
    started_at = time.time()

    try:
        proc = subprocess.run(
            command,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        exit_code = proc.returncode
        stdout = proc.stdout
        stderr = proc.stderr
    except subprocess.TimeoutExpired as exc:
        exit_code = -1
        # exc.stdout may be bytes when text=True is set but the process is
        # killed mid-stream; decode defensively to avoid a TypeError.
        raw_stdout = exc.stdout or b""
        stdout = raw_stdout.decode(errors="replace") if isinstance(raw_stdout, bytes) else raw_stdout
        stderr = f"Job timed out after {timeout}s"
    except Exception as exc:  # pragma: no cover
        exit_code = -1
        stdout = ""
        stderr = str(exc)

    duration = time.time() - started_at

    return JobResult(
        job_name=job_name,
        command=command,
        exit_code=exit_code,
        stdout=stdout.strip(),
        stderr=stderr.strip(),
        duration_seconds=round(duration, 4),
        started_at=started_at,
    )

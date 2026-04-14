"""Logging utilities for cronwatch.

Provides structured log file management for cron job execution records.
"""

import logging
import os
from datetime import datetime
from pathlib import Path


def get_log_path(log_dir: str, job_name: str) -> Path:
    """Return the log file path for a given job name."""
    safe_name = job_name.replace(" ", "_").replace("/", "-")
    return Path(log_dir) / f"{safe_name}.log"


def setup_job_logger(job_name: str, log_dir: str, level: str = "INFO") -> logging.Logger:
    """Create and configure a logger for a specific cron job.

    Args:
        job_name: Human-readable name for the cron job.
        log_dir: Directory where log files will be stored.
        level: Logging level string (DEBUG, INFO, WARNING, ERROR).

    Returns:
        Configured Logger instance.
    """
    os.makedirs(log_dir, exist_ok=True)

    log_path = get_log_path(log_dir, job_name)
    logger = logging.getLogger(f"cronwatch.job.{job_name}")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Avoid duplicate handlers on repeated calls
    if not logger.handlers:
        handler = logging.FileHandler(log_path)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def log_job_result(
    job_name: str,
    exit_code: int,
    duration: float,
    stdout: str,
    stderr: str,
    log_dir: str,
    level: str = "INFO",
) -> None:
    """Record the result of a cron job execution.

    Args:
        job_name: Name of the cron job.
        exit_code: Process exit code (0 = success).
        duration: Execution duration in seconds.
        stdout: Captured standard output.
        stderr: Captured standard error.
        log_dir: Directory to write logs.
        level: Base logging level.
    """
    logger = setup_job_logger(job_name, log_dir, level)
    status = "SUCCESS" if exit_code == 0 else "FAILURE"

    logger.info("job=%s status=%s exit_code=%d duration=%.3fs", job_name, status, exit_code, duration)

    if stdout.strip():
        logger.debug("stdout: %s", stdout.strip())

    if stderr.strip():
        log_fn = logger.error if exit_code != 0 else logger.warning
        log_fn("stderr: %s", stderr.strip())

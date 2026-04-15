"""High-level watcher that ties together runner, logger, history, notifier, and alerts."""

import logging
from typing import Dict, Any

from cronwatch.runner import run_job
from cronwatch.logger import setup_job_logger, log_job_result
from cronwatch.history import record_result
from cronwatch.notifier import build_failure_email, send_email_alert
from cronwatch.alerts import maybe_send_alert, clear_alert_state

log = logging.getLogger(__name__)


def execute_and_watch(job: Dict[str, Any], config: Dict[str, Any]) -> bool:
    """
    Run a single job, log the result, record history, and fire alerts if needed.

    Returns True if the job succeeded, False otherwise.
    """
    job_name: str = job["name"]
    command: str = job["command"]
    timeout: int = job.get("timeout", config.get("default_timeout", 3600))

    log_dir: str = config.get("log_dir", "/var/log/cronwatch")
    history_dir: str = config.get("history_dir", "/var/lib/cronwatch/history")
    state_dir: str = config.get("state_dir", "/var/lib/cronwatch/state")
    throttle: int = config.get("alert_throttle_seconds", 3600)

    job_logger = setup_job_logger(job_name, log_dir)
    result = run_job(job_name, command, timeout=timeout)
    log_job_result(job_logger, result)
    record_result(result, history_dir)

    if result.success:
        clear_alert_state(job_name, state_dir)
        log.debug("Job %s succeeded.", job_name)
        return True

    log.warning("Job %s FAILED (exit %s).", job_name, result.exit_code)

    email_cfg = config.get("email")
    if email_cfg and email_cfg.get("enabled", False):
        msg = build_failure_email(result, email_cfg)

        def _send():
            send_email_alert(msg, email_cfg)

        sent = maybe_send_alert(job_name, _send, state_dir, throttle_seconds=throttle)
        if not sent:
            log.info("Alert for %s suppressed by throttle.", job_name)

    return False

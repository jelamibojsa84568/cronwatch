"""Notification module for cronwatch — sends alerts on cron job failures."""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from cronwatch.runner import JobResult

logger = logging.getLogger(__name__)


def build_failure_email(
    result: JobResult,
    recipient: str,
    sender: str,
    hostname: Optional[str] = None,
) -> MIMEMultipart:
    """Construct a failure notification email for a given JobResult."""
    host_label = hostname or "unknown host"
    subject = f"[cronwatch] Job FAILED: {result.job_name} on {host_label}"

    body_lines = [
        f"Job '{result.job_name}' failed on {host_label}.",
        f"Exit code : {result.exit_code}",
        f"Duration  : {result.duration:.2f}s",
        "",
        "--- stdout ---",
        result.stdout.strip() or "(empty)",
        "",
        "--- stderr ---",
        result.stderr.strip() or "(empty)",
    ]
    body = "\n".join(body_lines)

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(body, "plain"))
    return msg


def send_email_alert(
    result: JobResult,
    config: dict,
    hostname: Optional[str] = None,
) -> bool:
    """
    Send an email alert if the job failed and email alerts are enabled.

    Returns True if an email was sent, False otherwise.
    """
    alert_cfg = config.get("alerts", {})
    if not alert_cfg.get("email_enabled", False):
        return False
    if result.success:
        return False

    smtp_host = alert_cfg.get("smtp_host", "localhost")
    smtp_port = int(alert_cfg.get("smtp_port", 25))
    sender = alert_cfg.get("sender", "cronwatch@localhost")
    recipient = alert_cfg.get("recipient", "root@localhost")

    msg = build_failure_email(result, recipient, sender, hostname)

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.sendmail(sender, [recipient], msg.as_string())
        logger.info("Alert email sent for job '%s' to %s", result.job_name, recipient)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to send alert email for job '%s': %s", result.job_name, exc)
        return False

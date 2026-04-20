"""Pre/post job hook execution support for cronwatch."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class HookPolicy:
    pre: List[str] = field(default_factory=list)
    post: List[str] = field(default_factory=list)
    on_failure: List[str] = field(default_factory=list)
    timeout: int = 30


def get_hook_policy(job_cfg: dict, global_cfg: dict) -> HookPolicy:
    """Build a HookPolicy from job-level config, falling back to global."""
    hooks_cfg = global_cfg.get("hooks", {})
    job_hooks = job_cfg.get("hooks", {})

    def _merge(key: str) -> List[str]:
        base = hooks_cfg.get(key, [])
        override = job_hooks.get(key, None)
        if override is not None:
            return override if isinstance(override, list) else [override]
        return base if isinstance(base, list) else [base]

    timeout = job_hooks.get("timeout", hooks_cfg.get("timeout", 30))
    return HookPolicy(
        pre=_merge("pre"),
        post=_merge("post"),
        on_failure=_merge("on_failure"),
        timeout=int(timeout),
    )


def _run_hook(command: str, timeout: int, context: str) -> bool:
    """Run a single hook command. Returns True on success."""
    logger.debug("Running %s hook: %s", context, command)
    try:
        result = subprocess.run(
            command,
            shell=True,
            timeout=timeout,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.warning(
                "%s hook failed (exit %d): %s",
                context,
                result.returncode,
                result.stderr.strip(),
            )
            return False
        return True
    except subprocess.TimeoutExpired:
        logger.error("%s hook timed out after %ds: %s", context, timeout, command)
        return False
    except Exception as exc:  # noqa: BLE001
        logger.error("%s hook raised an error: %s", context, exc)
        return False


def run_hooks(commands: List[str], timeout: int, context: str) -> List[bool]:
    """Run all hook commands for a given phase. Returns list of success flags."""
    return [_run_hook(cmd, timeout, context) for cmd in commands]

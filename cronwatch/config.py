"""Configuration loader for cronwatch."""

import os
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path.home() / ".cronwatch" / "config.yaml"

DEFAULT_CONFIG: dict[str, Any] = {
    "log_dir": str(Path.home() / ".cronwatch" / "logs"),
    "alert_on_failure": True,
    "retention_days": 30,
    "servers": [],
    "notify": {
        "email": None,
        "webhook": None,
    },
}


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load configuration from a YAML file, merging with defaults.

    Args:
        path: Path to the config file. Falls back to DEFAULT_CONFIG_PATH.

    Returns:
        Merged configuration dictionary.

    Raises:
        FileNotFoundError: If an explicit path is given but does not exist.
        yaml.YAMLError: If the config file contains invalid YAML.
    """
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH

    if path and not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    config = DEFAULT_CONFIG.copy()

    if config_path.exists():
        with config_path.open("r") as fh:
            user_config = yaml.safe_load(fh) or {}
        # Shallow merge; nested dicts (e.g. notify) are replaced entirely.
        config.update(user_config)

    # Allow environment variable overrides.
    if env_log_dir := os.environ.get("CRONWATCH_LOG_DIR"):
        config["log_dir"] = env_log_dir

    return config


def save_default_config(path: str | Path | None = None) -> Path:
    """Write the default configuration to disk.

    Args:
        path: Destination path. Falls back to DEFAULT_CONFIG_PATH.

    Returns:
        Path where the config was written.
    """
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with config_path.open("w") as fh:
        yaml.safe_dump(DEFAULT_CONFIG, fh, default_flow_style=False)

    return config_path

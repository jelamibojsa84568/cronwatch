# cronwatch

A lightweight CLI tool to monitor, log, and alert on cron job failures across multiple servers.

---

## Installation

```bash
pip install cronwatch
```

Or install from source:

```bash
git clone https://github.com/youruser/cronwatch.git && cd cronwatch && pip install .
```

---

## Usage

Add a cron job to cronwatch by wrapping your command:

```bash
cronwatch run --name "daily-backup" --alert email your_backup_script.sh
```

List all monitored jobs and their last status:

```bash
cronwatch list
```

View logs for a specific job:

```bash
cronwatch logs --name "daily-backup" --tail 50
```

Configure alert destinations in `~/.cronwatch/config.yaml`:

```yaml
alerts:
  email: ops@example.com
  slack_webhook: https://hooks.slack.com/services/xxx/yyy/zzz

servers:
  - host: web-01.example.com
  - host: web-02.example.com
```

Then monitor remote servers:

```bash
cronwatch monitor --server web-01.example.com
```

---

## Features

- Tracks exit codes, runtimes, and stdout/stderr for every job
- Sends alerts via email or Slack on failure or unexpected silence
- Supports multiple remote servers via SSH
- Simple YAML-based configuration

---

## License

This project is licensed under the [MIT License](LICENSE).
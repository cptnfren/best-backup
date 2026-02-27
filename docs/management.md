# Management CLI (bbman)

> Reference for `bbman`, the companion command that handles setup, health, updates, and maintenance for bbackup.

---

## Overview

`bbman` is a separate entry point from `bbackup`. Where `bbackup` runs backups and restores, `bbman` handles everything around the application: first-time setup, dependency checks, update management, diagnostics, and cleanup. You can use it as a pre-flight wrapper for `bbackup` runs or independently for maintenance.

---

## Command reference

### `bbman setup`

Interactive first-time setup wizard. Run this before anything else.

```bash
bbman setup
```

Checks Docker access, verifies `rsync` and `tar` are installed, installs any missing Python packages, and creates `~/.config/bbackup/config.yaml` if it does not exist. Optionally walks you through encryption key generation.

---

### `bbman health`

Comprehensive health check.

```bash
bbman health
```

Checks:
- Docker daemon is running and your user has socket access
- System tools: `rsync`, `tar`, `rclone`
- Python dependencies match `requirements.txt`
- Config file parses without errors
- Staging and log directories are writable

---

### `bbman check-deps`

Check (and optionally install) missing dependencies.

```bash
bbman check-deps              # Report only
bbman check-deps --install    # Install missing packages
bbman check-deps -i           # Shorthand
```

---

### `bbman validate-config`

Parse and validate the config file.

```bash
bbman validate-config
```

Reports YAML syntax errors, missing required fields, invalid paths, and unrecognized remote types. Shows a summary of what was parsed successfully.

---

### `bbman status`

Show backup history.

```bash
bbman status
```

Prints total backup count, combined size, how many are encrypted, and the most recent backup timestamps.

---

### `bbman cleanup`

Remove old staging files and logs.

```bash
bbman cleanup
bbman cleanup --staging-days 7    # Keep staging files newer than N days
bbman cleanup --log-days 30       # Keep log files newer than N days
bbman cleanup --yes               # Skip confirmation prompt
bbman cleanup --no-backups        # Do not touch old backup directories
bbman cleanup --no-temp           # Skip temporary file cleanup
```

---

### `bbman diagnostics`

Generate a diagnostic report.

```bash
bbman diagnostics
bbman diagnostics --output report.txt
```

Includes system info, Docker version, Python environment, config summary, and recent errors from the log file. Useful for bug reports.

---

### `bbman check-updates`

Check whether the installed version is behind the configured repository.

```bash
bbman check-updates
bbman check-updates --branch main
```

Uses SHA-256 checksums (Git-compatible) to compare local files against the remote tree. Reports which files have changed without downloading anything.

---

### `bbman update`

Pull updates from the repository.

```bash
bbman update
bbman update --method git       # Use git pull
bbman update --method download  # Download changed files directly
bbman update --yes              # Skip confirmation
```

Creates a backup of the current installation before applying changes. Verifies checksums after updating.

---

### `bbman repo-url`

Manage the repository URL used for update checks and downloads.

```bash
bbman repo-url                              # Show current URL and its source
bbman repo-url --url https://github.com/YOUR_USERNAME/best-backup
```

The URL is resolved in this order:

1. `BBACKUP_REPO_URL` environment variable
2. `repo_url` in `~/.config/bbackup/management.yaml`
3. Default compiled into `bbman.py`

---

### `bbman run`

Launch `bbackup` through the wrapper.

```bash
bbman run backup --containers myapp
bbman run list-containers
bbman run restore --backup-path /path/to/backup --all
```

Arguments pass through directly to `bbackup`. Use this if you want optional pre-flight health checks to run automatically before each backup.

---

## Management config file

`~/.config/bbackup/management.yaml` controls wrapper behavior:

```yaml
repo_url: "https://github.com/YOUR_USERNAME/best-backup"
auto_check_updates: true
check_interval_days: 7
auto_setup_on_first_run: true
health_check_before_run: false
update_method: "git"           # git, download, or manual
```

---

## First-run detection

On first launch, `bbman` checks for `~/.config/bbackup/config.yaml` and `~/.local/share/bbackup/.first_run_complete`. If either is missing, the setup wizard runs automatically. You can also trigger it manually at any time with `bbman setup`.

---

## Common workflows

### Initial setup

```bash
bbman setup
bbman health
bbman check-deps --install
bbman validate-config
```

### Before a backup run

```bash
bbman health
bbman run backup --backup-set production
```

### Maintenance

```bash
bbman status
bbman cleanup --yes
bbman diagnostics --output diagnostics.txt
```

### Update cycle

```bash
bbman check-updates
bbman update --yes
bbman health
```

---

## Troubleshooting

**Setup wizard does not appear automatically**

Run it directly: `bbman setup`

**Update fails**

```bash
bbman repo-url                          # Confirm URL is correct
bbman diagnostics --output report.txt   # Check for errors
cat ~/.local/share/bbackup/bbackup.log  # Review recent log entries
```

**Health check failures**

| Symptom | Fix |
|---|---|
| Docker not accessible | `sudo usermod -aG docker $USER && newgrp docker` |
| Missing Python packages | `bbman check-deps --install` |
| Config parse error | `bbman validate-config` for details |
| rsync not found | `sudo apt-get install rsync` |

---

Back to [README.md](../README.md).

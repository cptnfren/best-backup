# bbackup

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A Docker backup tool with a full-screen terminal UI. It handles containers, volumes, networks, and configurations in one shot, with incremental backups, encryption at rest, and automatic rotation to local or remote storage.

---

## What it does

Run `bbackup backup` and you get an interactive container picker, a live BTOP-style dashboard while the backup runs, and a finished archive that can be encrypted and shipped to Google Drive, SFTP, or a local path. The companion `bbman` command handles setup, health checks, dependency installs, and self-updates so day-to-day maintenance stays out of the way.

## Features

| | |
|---|---|
| ✅ Rich TUI | BTOP-style live dashboard with real-time transfer metrics |
| ✅ Incremental backups | rsync `--link-dest` so unchanged data is hardlinked, not copied |
| ✅ Encryption | AES-256-GCM (symmetric) or RSA-4096 (asymmetric) at rest |
| ✅ Remote storage | Google Drive via rclone, SFTP, or local directory |
| ✅ Rotation | Time-based daily/weekly/monthly retention with quota enforcement |
| ✅ Full restore | Containers, volumes, networks, and filesystem paths with optional rename |
| ✅ Backup sets | Named groups of containers defined in config for repeatable runs |
| ✅ Filesystem backup | Back up any host path recursively with gitignore-style exclude patterns |
| ✅ Management CLI | `bbman` for setup, health, updates, cleanup, and diagnostics |

---

## Requirements

- Python 3.10+
- Docker (with socket access for your user)
- `rsync` (system package, for volume backups)
- `rclone` (optional, for Google Drive)

---

## Installation

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/best-backup.git
cd best-backup

# Install Python dependencies and register system commands
pip install -e .
```

Both `bbackup` and `bbman` will be available system-wide after this.

For other installation methods (symlinks, PATH-only, user install), see [INSTALL.md](INSTALL.md).

---

## Quick start

```bash
# First-time setup (checks Docker, dependencies, creates config)
bbman setup

# Run an interactive backup
bbackup backup

# Or target specific containers
bbackup backup --containers myapp mydb
```

See [QUICKSTART.md](QUICKSTART.md) for a complete walk-through including config, remote storage, and encryption setup.

---

## Configuration

bbackup looks for config in this order:

1. `~/.config/bbackup/config.yaml`
2. `~/.bbackup/config.yaml`
3. `/etc/bbackup/config.yaml`
4. `./config.yaml`

A full annotated example is in [`config.yaml.example`](config.yaml.example). The minimal pieces you need:

```yaml
backup:
  local_staging: /tmp/bbackup_staging
  backup_sets:
    production:
      containers: [myapp, mydb, nginx]
      scope:
        volumes: true
        configs: true

remotes:
  local:
    enabled: true
    type: local
    path: ~/backups/docker
```

To back up local filesystem paths, add a `filesystem:` section:

```yaml
filesystem:
  home-data:
    description: "Important home directory data"
    targets:
      - name: documents
        path: /home/user/Documents
        enabled: true
        excludes:
          - "*.tmp"
          - ".cache/"
          - "node_modules/"
```

Run these sets with `bbackup backup --filesystem-set home-data`, or pass paths directly with `--paths`.

---

## CLI reference

### `bbackup` commands

```bash
bbackup backup                                  # Interactive backup with TUI
bbackup backup --backup-set production          # Use a named backup set
bbackup backup --containers app db              # Pick specific containers
bbackup backup --incremental                    # rsync --link-dest mode
bbackup backup --config-only                    # Skip volumes
bbackup backup --volumes-only                   # Skip configs
bbackup backup --no-networks                    # Skip network configs
bbackup backup --remote gdrive                  # Upload to specific remote

# Filesystem backup (non-Docker paths)
bbackup backup --paths /home/user/docs /srv/data            # Back up specific paths
bbackup backup --paths /home/user/docs --exclude "*.tmp"    # With exclude patterns
bbackup backup --filesystem-set home-data                   # Named set from config

bbackup restore --backup-path /path/to/backup --all
bbackup restore --backup-path /path --containers app --rename app:app_v2

# Filesystem restore
bbackup restore --backup-path /path --filesystem documents --filesystem-destination /home/user/docs

bbackup list-containers
bbackup list-backup-sets
bbackup list-filesystem-sets
bbackup list-backups
bbackup list-remote-backups --remote gdrive

bbackup init-config
bbackup init-encryption --method asymmetric --algorithm rsa-4096
```

### `bbman` commands

```bash
bbman setup                    # First-time setup wizard
bbman health                   # Docker, tools, config health check
bbman check-deps               # Check dependencies
bbman check-deps --install     # Install missing packages
bbman validate-config          # Parse and validate config file
bbman status                   # Backup history and totals
bbman cleanup                  # Clean staging dirs and old logs
bbman diagnostics              # Generate diagnostic report
bbman check-updates            # Check for newer version
bbman update                   # Self-update from repo
bbman repo-url --url URL       # Set the update source URL
bbman run backup --containers app  # Run bbackup through the wrapper
```

---

## TUI keyboard controls

| Key | Action |
|-----|--------|
| `Q` | Quit / cancel backup |
| `P` | Pause / resume |
| `S` | Skip current item |
| `H` | Help |

---

## Encryption

Two modes are supported:

**Symmetric (AES-256-GCM):** One key encrypts and decrypts. Good for single-server setups.

```bash
bbackup init-encryption --method symmetric
```

**Asymmetric (RSA-4096):** Public key encrypts, private key decrypts. Better for multi-server setups where you want separate backup and restore machines.

```bash
bbackup init-encryption --method asymmetric --algorithm rsa-4096
```

The public key can be hosted on GitHub and referenced by shortcut:

```yaml
encryption:
  enabled: true
  method: asymmetric
  asymmetric:
    public_key: github:YOUR_USERNAME/gist:YOUR_GIST_ID
    private_key: ~/.config/bbackup/backup_private.pem
```

Full details in [docs/encryption.md](docs/encryption.md).

---

## Project structure

```
best-backup/
├── bbackup/                # Main Python package
│   ├── cli.py                  # bbackup CLI entry point
│   ├── config.py               # Config loading and all dataclasses
│   ├── docker_backup.py        # Docker backup via temp Alpine containers
│   ├── filesystem_backup.py    # Host filesystem backup via rsync
│   ├── backup_runner.py        # Backup workflow orchestration
│   ├── restore.py              # Restore operations
│   ├── tui.py                  # Rich TUI and BackupStatus tracking
│   ├── remote.py               # Remote storage (local / rclone / SFTP)
│   ├── rotation.py             # Retention policies and quota cleanup
│   ├── encryption.py           # AES-256-GCM + RSA encryption
│   ├── logging.py              # Rotating file logger
│   ├── bbman_entry.py          # Console script shim for bbman
│   └── management/             # bbman subpackage (11 modules)
├── bbackup.py              # bbackup entry point
├── bbman.py                # bbman entry point
├── config.yaml.example     # Annotated config template
├── requirements.txt
└── setup.py
```

---

## Documentation

- [QUICKSTART.md](QUICKSTART.md) - Setup to first backup in 5 minutes
- [INSTALL.md](INSTALL.md) - All installation methods
- [docs/management.md](docs/management.md) - Full `bbman` reference
- [docs/encryption.md](docs/encryption.md) - Encryption setup and key management

---

## Roadmap

**Done**

- [x] Rich TUI with real-time transfer metrics
- [x] Incremental backups with rsync `--link-dest`
- [x] Backup rotation and retention policies
- [x] AES-256-GCM and RSA-4096 encryption
- [x] Full restore with optional rename
- [x] Filesystem backup for arbitrary host paths and directory trees
- [x] Management wrapper (`bbman`)
- [x] GitHub key integration for public key distribution

**Planned**

- [ ] Backup verification and checksums
- [ ] Email and webhook notifications
- [ ] Cron-based scheduling integration
- [ ] Multi-server backup coordination
- [ ] Backup diff / comparison
- [ ] Web UI

---

## License

MIT.

---

## Credits

- Terminal UI via [Rich](https://github.com/Textualize/rich)
- CLI framework via [Click](https://github.com/pallets/click)
- Docker integration via [docker-py](https://github.com/docker/docker-py)

<!-- project-footer:start -->

<br><br>

<p align="center">
Slavic Kozyuk<br>
&copy; 2026 <a href="https://www.cruxexperts.com/">Crux Experts LLC</a> &mdash; <a href="https://github.com/cptnfren/best-backup/blob/main/LICENSE">MIT License</a>
</p>

<!-- project-footer:end -->

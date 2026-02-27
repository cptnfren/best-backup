# bbackup Project Summary

## Overview

**bbackup** is a comprehensive Docker backup tool with a rich terminal user interface (TUI) built using Python 3 and the Rich library. It provides efficient backup of Docker containers, volumes, networks, and configurations with support for incremental backups, remote storage, and intelligent rotation policies.

## Architecture Decisions

### Technology Stack
- **Language**: Python 3.10+ (tested on 3.12)
- **TUI Library**: Rich 13.7.0+ (BTOP-like interface)
- **CLI Framework**: Click 8.1.7+
- **Config Format**: YAML (PyYAML 6.0.1+)
- **Docker Integration**: docker SDK 7.0.0+
- **Remote Storage**: rclone (optional), paramiko 3.4.0+ (SFTP)
- **Encryption**: cryptography 41.0.0+ (AES-256-GCM, RSA/ECDSA)
- **HTTP**: requests 2.31.0+ (key URL fetching)

### Backup Strategy
- **Hybrid Approach**: rsync for volumes, tar for metadata
- **Incremental Support**: rsync `--link-dest` for efficient differential backups
- **Compression**: Configurable (gzip, bzip2, xz)

### Key Features Implemented
✅ Rich TUI interface with progress bars and status displays  
✅ Docker container, volume, and network backup  
✅ Incremental/differential backups with --link-dest  
✅ Multiple remote storage destinations (rclone, SFTP, local)  
✅ Backup rotation with time-based retention (fully integrated)  
✅ Storage quota management with automatic cleanup  
✅ YAML configuration with CLI overrides  
✅ Interactive container selection  
✅ Backup sets (predefined container groups)  
✅ Selective backup (config-only, volumes-only, etc.)  
✅ Logging system with file rotation  
✅ Volume compression support  
✅ Upload progress tracking  
✅ Skip functionality (S key) - console output; modal overlay planned  
✅ Help screen (H key) - console output; modal overlay planned  
✅ Backup encryption (AES-256-GCM symmetric, RSA-4096 asymmetric)  
✅ Management wrapper (bbman) - first-run, health, updates, diagnostics  
✅ List remote backups command  

## Project Structure

```
best-backup/
├── bbackup/                 # Main package
│   ├── __init__.py         # Package initialization
│   ├── cli.py              # bbackup CLI commands and entry point
│   ├── config.py           # Config loading, parsing, all dataclasses
│   ├── docker_backup.py    # Docker backup via temp containers
│   ├── backup_runner.py    # Workflow orchestration + BackupStatus
│   ├── restore.py          # Restore operations
│   ├── tui.py              # Rich TUI, live dashboard, BackupStatus
│   ├── remote.py           # Remote storage (local/rclone/SFTP)
│   ├── rotation.py         # Retention policies, quota cleanup
│   ├── encryption.py       # AES-256-GCM + RSA/ECDSA encryption
│   ├── logging.py          # get_logger() factory, rotating file handler
│   ├── bbman_entry.py      # Console script shim for bbman
│   └── management/         # Lifecycle management subpackage
│       └── ...             # (11 modules: first_run, health, updater, etc.)
├── bbackup.py              # bbackup entry point
├── bbman.py                # bbman management CLI
├── config.yaml.example     # Example configuration file
├── requirements.txt        # Python dependencies
├── setup.py                # Package setup
├── README.md               # Full documentation
├── QUICKSTART.md           # Quick start guide
└── PROJECT_SUMMARY.md      # This file
```

## Module Breakdown

### `bbackup/cli.py`
- bbackup CLI entry point using Click
- Commands: `backup`, `restore`, `list-containers`, `list-backup-sets`, `list-backups`, `list-remote-backups`, `init-config`, `init-encryption`
- Arg parsing and delegation to `BackupRunner`, `DockerRestore`, etc.

### `bbackup/config.py`
- YAML configuration loading and parsing
- Configuration file discovery (priority chain)
- All dataclasses: `BackupScope`, `BackupSet`, `RemoteStorage`, `RetentionPolicy`, `IncrementalSettings`, `EncryptionSettings`, `Config`
- Config merging (file defaults + CLI overrides)

### `bbackup/docker_backup.py`
- Docker API integration via temp Alpine containers
- Container config, volume, and network backup
- rsync with `--link-dest` for incremental volume backups
- tar for metadata archives
- Volume compression (configurable format)

### `bbackup/backup_runner.py`
- Workflow orchestration: init → select → backup → encrypt → upload → rotate → report
- `BackupStatus` consumer (updates via `status.update()`, `add_error()`, etc.)
- Integrates `BackupRotation` post-upload
- Calls `EncryptionManager` if encryption enabled

### `bbackup/restore.py`
- Full restore of containers, volumes, and networks from backup directory
- Rename-on-restore support
- Decryption before restore if backup is encrypted

### `bbackup/tui.py`
- `BackupStatus` class (thread-safe, lock-protected)
- `BackupTUI` with BTOP-like live dashboard (4 refreshes/sec)
- Interactive container selection, backup set selection, scope dialogs
- Keyboard: Q=quit, P=pause/resume, S=skip (console), H=help (console)

### `bbackup/remote.py`
- Remote storage abstraction: local (shutil), rclone, SFTP (paramiko)
- Multi-remote upload; per-remote failures don't abort others
- Upload progress tracking; status via `BackupStatus.remote_status`

### `bbackup/rotation.py`
- Retention: daily/weekly/monthly, oldest-first cleanup
- Storage quota checking (warning + cleanup thresholds)
- Fully integrated in `backup_runner.py` post-upload

### `bbackup/encryption.py`
- AES-256-GCM symmetric encryption (per-file random IV)
- RSA-OAEP + AES hybrid for asymmetric mode
- Key sources: local file, URL, or GitHub gist shortcut (`github:USER/gist:ID`)
- URL-fetched keys cached at `~/.cache/bbackup/keys/` (chmod 600)

### `bbackup/logging.py`
- `get_logger(name)` factory used by all modules
- `setup_logging(config)` configures rotating file handler on startup
- Log path: `~/.local/share/bbackup/bbackup.log`

### `bbackup/management/`
- 11-module subpackage for lifecycle operations
- Key modules: `first_run`, `setup_wizard`, `health`, `diagnostics`, `updater`, `version`, `repo`, `dependencies`, `cleanup`
- Exposed via `bbman.py` (management CLI separate from backup CLI)

## Configuration System

### Configuration File Locations (in order)
1. `~/.config/bbackup/config.yaml`
2. `~/.bbackup/config.yaml`
3. `/etc/bbackup/config.yaml`
4. `./config.yaml` (current directory)

### Configuration Sections
- **backup**: Backup settings, backup sets, default scope
- **remotes**: Remote storage destinations
- **retention**: Rotation and retention policies
- **incremental**: Incremental backup settings
- **logging**: Logging configuration
- **docker**: Docker-specific settings

### CLI Override System
- Config file provides defaults
- CLI arguments override config values
- Interactive mode allows runtime selection

## Usage Patterns

### Interactive Mode (Default)
```bash
bbackup backup
# Shows TUI for container selection and scope
```

### Automated Mode
```bash
bbackup backup --backup-set production --no-interactive
# Uses config-defined backup set
```

### Selective Backup
```bash
bbackup backup --containers dms minio --config-only
# Backup specific containers, configs only
```

### Incremental Backup
```bash
bbackup backup --incremental
# Uses rsync --link-dest for efficiency
```

## Dependencies

### Required
- `rich>=13.7.0` - TUI library
- `pyyaml>=6.0.1` - YAML parsing
- `docker>=7.0.0` - Docker SDK
- `click>=8.1.7` - CLI framework
- `paramiko>=3.4.0` - SFTP support
- `cryptography>=41.0.0` - AES-256-GCM + RSA encryption
- `requests>=2.31.0` - HTTP key fetching

### External Tools
- `rsync` - Volume backups (system package)
- `rclone` - Cloud storage (optional, external install)

## Completed Features ✅

- ✅ Restore functionality - Full restore of containers, volumes, and networks
- ✅ Backup encryption - AES-256-GCM (symmetric) and RSA-4096 (asymmetric)
- ✅ Management wrapper - Comprehensive `bbman.py` for setup, health, updates
- ✅ Real-time metrics - Transfer speed, bytes transferred, file counts
- ✅ GitHub key integration - Easy encryption key deployment
- ✅ File-level version checking - Git-compatible checksums

## Future Enhancements (Roadmap)

- [ ] Backup verification/checksums
- [ ] Email notifications
- [ ] Webhook support
- [ ] Backup scheduling (cron integration)
- [ ] Multi-server backup coordination
- [ ] Backup comparison/diff
- [ ] Web UI for backup management

## Testing & Verification

### Basic Verification
```bash
# Check Python syntax
python3 -m py_compile bbackup/*.py

# Test imports
python3 -c "from bbackup.config import Config; print('OK')"

# Test Docker connection
python3 -c "from bbackup.docker_backup import DockerBackup; from bbackup.config import Config; DockerBackup(Config())"
```

### Manual Testing
1. Initialize config: `bbackup init-config`
2. List containers: `bbackup list-containers`
3. Create test backup: `bbackup backup --containers <test_container>`
4. Verify backup created in staging directory

## Distribution

This project is designed to be extracted into its own GitHub repository. The structure supports:

- **Direct execution**: `./bbackup.py backup`
- **System installation**: `pip install -e .` then `bbackup backup`
- **Package distribution**: `python setup.py sdist bdist_wheel`

## License

Part of the Linux Tools repository. To be determined when extracted.

## Author Notes

- Designed for Linux server environments
- Requires Docker socket access
- Optimized for large volume backups
- Supports both interactive and automated workflows
- Configuration-first approach with CLI flexibility

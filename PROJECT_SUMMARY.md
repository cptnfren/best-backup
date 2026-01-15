# bbackup Project Summary

## Overview

**bbackup** is a comprehensive Docker backup tool with a rich terminal user interface (TUI) built using Python 3 and the Rich library. It provides efficient backup of Docker containers, volumes, networks, and configurations with support for incremental backups, remote storage, and intelligent rotation policies.

## Architecture Decisions

### Technology Stack
- **Language**: Python 3.8+
- **TUI Library**: Rich (for BTOP-like interface)
- **CLI Framework**: Click
- **Config Format**: YAML
- **Docker Integration**: docker SDK for Python
- **Remote Storage**: rclone (Google Drive), paramiko (SFTP)

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
✅ Skip functionality (S key)  
✅ Help screen (H key)  
✅ List remote backups command  

## Project Structure

```
best-backup/
├── bbackup/                 # Main package
│   ├── __init__.py         # Package initialization
│   ├── cli.py              # CLI entry point and commands
│   ├── config.py           # Configuration management
│   ├── docker_backup.py    # Docker backup operations
│   ├── tui.py              # Rich TUI interface
│   ├── remote.py           # Remote storage integration
│   └── rotation.py         # Backup rotation logic
├── bbackup.py              # Main executable script
├── config.yaml.example     # Example configuration file
├── requirements.txt        # Python dependencies
├── setup.py                # Package setup for future distribution
├── README.md               # Full documentation
├── QUICKSTART.md           # Quick start guide
├── PROJECT_SUMMARY.md      # This file
└── .gitignore             # Git ignore rules
```

## Module Breakdown

### `bbackup/cli.py`
- Main CLI entry point using Click
- Commands: `backup`, `list-containers`, `list-backup-sets`, `init-config`
- Handles CLI argument parsing and delegation to other modules

### `bbackup/config.py`
- YAML configuration loading and parsing
- Configuration file discovery (multiple standard locations)
- Dataclasses for type-safe configuration
- Config merging (file defaults + CLI overrides)

### `bbackup/docker_backup.py`
- Docker API integration
- Container, volume, and network backup operations
- rsync integration for volume backups
- tar integration for metadata archives
- Incremental backup support

### `bbackup/tui.py`
- Rich TUI interface components
- Interactive container selection
- Progress displays and status panels
- Backup set selection interface
- Scope selection dialogs

### `bbackup/remote.py`
- Remote storage abstraction
- rclone integration (Google Drive, etc.)
- SFTP integration (paramiko)
- Local directory support
- Upload progress tracking

### `bbackup/rotation.py`
- Backup retention policy management
- Time-based categorization (daily/weekly/monthly)
- Storage quota checking
- Automatic cleanup of old backups
- Backup filtering by retention rules

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

### External Tools
- `rsync` - For volume backups (system package)
- `rclone` - For Google Drive support (optional, external install)

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

# bbackup - Docker Backup Tool

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A comprehensive, production-ready Docker backup solution with a beautiful Rich TUI interface. Backs up Docker containers, volumes, networks, and configurations with support for incremental backups, remote storage, encryption, and intelligent rotation policies.

## ✨ Features

### Core Functionality
- 🎨 **Rich TUI Interface** - Beautiful BTOP-like terminal interface with real-time metrics
- 🐳 **Full Docker Integration** - Complete backup of containers, volumes, networks, and metadata
- 📦 **Hybrid Backup Strategy** - rsync for volumes (efficient), tar for metadata (structured)
- 🔄 **Incremental Backups** - Only backup changes using rsync `--link-dest` for space efficiency
- 🔐 **Data Encryption** - AES-256-GCM (symmetric) and RSA-4096 (asymmetric) encryption at rest
- ☁️ **Remote Storage** - Google Drive (rclone), SFTP, local directories
- 🔁 **Backup Rotation** - Time-based retention with automatic storage quota management
- 📊 **Real-Time Metrics** - Transfer speed, bytes transferred, file counts, progress tracking
- ⚙️ **Flexible Configuration** - YAML config files with CLI overrides
- 🎯 **Selective Backup** - Choose specific containers, volumes, or backup sets
- 📝 **Comprehensive Logging** - File-based logging with rotation
- ⌨️ **Interactive Controls** - Q (quit), P (pause), S (skip), H (help)
- 🔧 **Management Wrapper** - `bbman.py` for setup, health checks, updates, and diagnostics

### Advanced Features
- **Restore Functionality** - Full restore of containers, volumes, and networks
- **Backup Sets** - Predefined groups of containers for organized backups
- **Encryption Key Management** - GitHub integration for easy key deployment
- **File-Level Version Checking** - Git-compatible checksums for update detection
- **Health Diagnostics** - Comprehensive system health checks
- **Automatic Cleanup** - Intelligent cleanup of old backups and logs

## 📋 Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage](#usage)
- [Features in Detail](#features-in-detail)
- [Management Wrapper](#management-wrapper)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [License](#license)

## 🚀 Installation

### Prerequisites

- Python 3.8+
- Docker (with Docker socket access)
- rsync (for volume backups)
- rclone (optional, for Google Drive support)

### Quick Install (Recommended)

Use the management wrapper for the easiest setup:

```bash
# Clone or navigate to the repository
cd best-backup

# Make management script executable
chmod +x bbman.py

# Run interactive setup wizard
python3 bbman.py setup
```

The setup wizard will:
- Check Docker access
- Verify system dependencies
- Check Python packages
- Create configuration file
- Optionally set up encryption keys

### Manual Installation

```bash
# Install Python dependencies
pip install -r requirements.txt

# Make scripts executable
chmod +x bbackup.py bbman.py

# Initialize configuration
python3 bbackup.py init-config
```

### Install as System Command

**Recommended:** Install via pip to register as system commands:

```bash
# Development mode (editable, changes take effect immediately)
pip3 install -e .

# Or normal install (copies files)
pip3 install .
```

After installation, both `bbackup` and `bbman` are available as system commands from anywhere.

**Alternative:** Create symlinks (quick, no installation):
```bash
# Make scripts executable
chmod +x bbackup.py bbman.py

# Create symlinks (requires sudo)
sudo ln -s $(pwd)/bbackup.py /usr/local/bin/bbackup
sudo ln -s $(pwd)/bbman.py /usr/local/bin/bbman
```

**Verify installation:**
```bash
which bbackup
which bbman
bbackup --version
bbman --version
```

## 🎯 Quick Start

### 1. Initial Setup

```bash
# Run setup wizard (recommended)
python3 bbman.py setup

# Or manually initialize config
python3 bbackup.py init-config
```

### 2. Edit Configuration

Edit `~/.config/bbackup/config.yaml`:

```yaml
backup:
  local_staging: /tmp/bbackup_staging
  backup_sets:
    production:
      description: "Production containers"
      containers:
        - container1
        - container2
      scope:
        volumes: true
        configs: true

remotes:
  local:
    enabled: true
    type: local
    path: ~/backups/docker
```

### 3. Run Your First Backup

```bash
# Interactive mode (select containers from menu)
python3 bbackup.py backup

# Or use management wrapper
python3 bbman.py run backup

# Backup specific containers
python3 bbackup.py backup --containers container1 container2

# Use backup set
python3 bbackup.py backup --backup-set production
```

## ⚙️ Configuration

### Configuration File Locations

bbackup looks for configuration in this order:
1. `~/.config/bbackup/config.yaml` (recommended)
2. `~/.bbackup/config.yaml`
3. `/etc/bbackup/config.yaml`
4. `./config.yaml` (current directory)

### Configuration Sections

See `config.yaml.example` for a complete example. Key sections:

**Backup Sets:**
```yaml
backup:
  backup_sets:
    production:
      description: "Production containers"
      containers:
        - dms
        - minio
        - npm
      scope:
        volumes: true
        configs: true
        networks: true
```

**Remote Storage:**
```yaml
remotes:
  gdrive:
    enabled: true
    type: rclone
    remote_name: gdrive
    path: /backups/docker
  
  sftp_server:
    enabled: true
    type: sftp
    host: backup.example.com
    port: 22
    user: backup
    key_file: ~/.ssh/backup_key
    path: /backups/docker
```

**Retention Policy:**
```yaml
retention:
  daily: 7
  weekly: 4
  monthly: 12
  max_storage_gb: 100
  cleanup_threshold_percent: 90
```

**Encryption:**
```yaml
encryption:
  enabled: true
  method: asymmetric
  asymmetric:
    public_key: github:USERNAME  # Auto-resolves from GitHub
    private_key: ~/.config/bbackup/backup_private.pem
```

## 📖 Usage

### CLI Commands

#### Backup Operations

```bash
# Interactive backup (default)
bbackup backup

# Backup specific containers
bbackup backup --containers dms minio npm

# Use backup set
bbackup backup --backup-set production

# Configuration only (no volumes)
bbackup backup --config-only

# Volumes only (no configs)
bbackup backup --volumes-only

# Incremental backup
bbackup backup --incremental

# Skip networks
bbackup backup --no-networks

# Upload to specific remotes
bbackup backup --remote gdrive --remote sftp_server
```

#### Restore Operations

```bash
# Restore all from backup
bbackup restore --backup-path /path/to/backup --all

# Restore specific containers
bbackup restore --backup-path /path/to/backup --containers container1 container2

# Restore with renaming
bbackup restore --backup-path /path/to/backup --containers old_name --rename old_name:new_name

# Restore volumes only
bbackup restore --backup-path /path/to/backup --volumes volume1 volume2
```

#### Information Commands

```bash
# List all containers
bbackup list-containers

# List backup sets
bbackup list-backup-sets

# List local backups
bbackup list-backups

# List backups on remote storage
bbackup list-remote-backups --remote gdrive
```

#### Encryption Setup

```bash
# Initialize symmetric encryption
bbackup init-encryption --method symmetric

# Initialize asymmetric encryption
bbackup init-encryption --method asymmetric --algorithm rsa-4096

# Upload public key to GitHub
bbackup init-encryption --method asymmetric --upload-github
```

### CLI Options

```
Global Options:
  --config, -c         Path to configuration file
  --version            Show version information

Backup Options:
  --containers, -C     Container names to backup (multiple)
  --backup-set, -s    Use predefined backup set
  --config-only       Backup only configurations
  --volumes-only      Backup only volumes
  --no-networks       Skip network backups
  --incremental, -i   Use incremental backup
  --remote, -r        Remote storage destinations (multiple)
  --no-interactive    Disable interactive mode
```

## 🎨 Features in Detail

### Rich TUI Interface

The TUI provides a BTOP-like interface with:

- **Real-Time Metrics:**
  - Transfer speed (MB/s or GB/s)
  - Bytes transferred (KB/MB/GB)
  - Files transferred count
  - Current file being processed
  - Progress percentage
  - Elapsed time and ETA

- **Live Dashboard:**
  - Header with status and metrics
  - Containers panel with backup status
  - Volumes panel with backup status
  - Progress bar with detailed information
  - Status panel with errors/warnings
  - Footer with keyboard controls

- **Keyboard Controls:**
  - **Q** - Quit/Cancel backup
  - **P** - Pause/Resume backup
  - **S** - Skip current item
  - **H** - Show help screen

### Backup Strategy

#### Hybrid Approach

- **Volumes**: Backed up using `rsync` for efficiency with large files
  - Supports incremental backups via `--link-dest`
  - Handles sparse files and large datasets efficiently
  - Real-time progress tracking with transfer speed

- **Metadata**: Backed up using `tar` with compression
  - Container configurations (docker inspect)
  - Network configurations
  - Container logs
  - Backup metadata

#### Incremental Backups

When `--incremental` is used or `incremental.enabled: true` in config:
- rsync uses `--link-dest` to reference previous backups
- Only changed files are copied
- Unchanged files are hardlinked (saves space)
- Works best for volumes with large, slowly-changing data
- Automatically finds previous backup for each volume

### Encryption

bbackup supports encryption at rest with two methods:

#### Symmetric Encryption (AES-256-GCM)
- Single key for encryption/decryption
- Faster performance
- Best for single-server deployments

#### Asymmetric Encryption (RSA-4096)
- Public/private key pair
- Public key can be safely shared
- Best for multi-server deployments
- Supports GitHub integration for easy key deployment

**GitHub Integration:**
```yaml
encryption:
  enabled: true
  method: asymmetric
  asymmetric:
    public_key: github:USERNAME  # Auto-resolves from GitHub
```

### Remote Storage

#### Google Drive (rclone)

1. Configure rclone:
   ```bash
   rclone config
   ```

2. Add to config:
   ```yaml
   remotes:
     gdrive:
       enabled: true
       type: rclone
       remote_name: gdrive
       path: /backups/docker
   ```

#### SFTP

```yaml
remotes:
  ssh_server:
    enabled: true
    type: sftp
    host: backup.example.com
    port: 22
    user: backup
    key_file: ~/.ssh/backup_key
    path: /backups/docker
```

#### Local Directory

```yaml
remotes:
  local:
    enabled: true
    type: local
    path: ~/backups/docker
```

### Backup Rotation

#### Time-Based Retention

- **Daily**: Keep N most recent daily backups
- **Weekly**: Keep N weekly backups (typically Sunday backups)
- **Monthly**: Keep N monthly backups (first of month)
- Automatically integrated into backup workflow

#### Storage Quota Management

When storage quota is configured:
- Warns when storage exceeds warning threshold
- Automatically cleans up old backups when cleanup threshold is reached
- Deletes oldest backups first (configurable strategy)
- Runs automatically after each backup upload

## 🔧 Management Wrapper

The `bbman.py` wrapper provides comprehensive application management:

### Setup

```bash
bbman setup
```

Interactive setup wizard for first-time configuration.

### Health Check

```bash
bbman health
```

Comprehensive health check:
- Docker daemon accessibility
- System tools (rsync, tar, rclone)
- Python dependencies
- Configuration file validity
- Directory permissions

### Dependency Management

```bash
bbman check-deps
bbman check-deps --install  # Install missing packages
```

### Configuration Validation

```bash
bbman validate-config
```

### Backup Status

```bash
bbman status
```

Show backup status and history.

### Cleanup

```bash
bbman cleanup
bbman cleanup --staging-days 7 --log-days 30
bbman cleanup --yes  # Skip confirmation
```

### Diagnostics

```bash
bbman diagnostics
bbman diagnostics --output report.txt
```

### Update Management

```bash
# Check for updates
bbman check-updates

# Update application
bbman update
bbman update --method git  # Use Git method
bbman update --yes  # Skip confirmation
```

### Repository URL Management

```bash
# Show current repository URL
bbman repo-url

# Set repository URL
bbman repo-url https://github.com/user/repo
```

### Run Application

```bash
# Launch bbackup through wrapper
bbman run backup --containers my_container
bbman run list-containers
```

For detailed management guide, see [docs/MANAGEMENT_GUIDE.md](docs/MANAGEMENT_GUIDE.md).

## 🐛 Troubleshooting

### Docker Permission Issues

```bash
# Add user to docker group
sudo usermod -aG docker $USER
# Log out and back in, or:
newgrp docker
```

### rclone Not Found

```bash
# Install rclone
curl https://rclone.org/install.sh | sudo bash
```

### rsync Not Available

```bash
# Install rsync
sudo apt-get install rsync  # Debian/Ubuntu
sudo yum install rsync      # RHEL/CentOS
```

### TUI Not Displaying

The TUI requires an interactive terminal. If output is piped, it will display in non-screen mode. Run directly in a terminal:

```bash
# This will show full-screen TUI
python3 bbackup.py backup

# This will show TUI but truncated
python3 bbackup.py backup | head -20
```

### Configuration Not Found

```bash
# Initialize configuration
python3 bbackup.py init-config

# Or use management wrapper
python3 bbman.py setup
```

## 🛠️ Development

### Running from Source

```bash
# Install in development mode
pip install -e .

# Or run directly
python3 bbackup.py backup
```

### Testing

```bash
# Test Docker connection
python3 -c "from bbackup.docker_backup import DockerBackup; from bbackup.config import Config; DockerBackup(Config())"

# Test config loading
python3 -c "from bbackup.config import Config; c = Config(); print(c.data)"

# Run health check
python3 bbman.py health
```

### Project Structure

```
best-backup/
├── bbackup/              # Main package
│   ├── __init__.py
│   ├── cli.py           # CLI entry point
│   ├── config.py        # Configuration management
│   ├── docker_backup.py # Docker backup logic
│   ├── backup_runner.py # Backup orchestration
│   ├── restore.py       # Restore operations
│   ├── tui.py           # Rich TUI interface
│   ├── remote.py        # Remote storage integration
│   ├── rotation.py      # Backup rotation logic
│   ├── encryption.py    # Encryption management
│   ├── logging.py       # Logging system
│   └── management/      # Management utilities
│       ├── health.py
│       ├── diagnostics.py
│       ├── updater.py
│       └── ...
├── bbackup.py           # Main CLI script
├── bbman.py             # Management wrapper
├── config.yaml.example  # Example configuration
├── requirements.txt     # Python dependencies
├── setup.py             # Package setup
└── README.md            # This file
```

## 📚 Additional Documentation

- [Quick Start Guide](QUICKSTART.md) - 5-minute setup guide
- [Quick Install Guide](QUICK_INSTALL.md) - Installation instructions
- [Management Guide](docs/MANAGEMENT_GUIDE.md) - Complete bbman.py documentation
- [Encryption Guide](docs/ENCRYPTION_GUIDE.md) - Encryption setup and key management
- [Project Summary](PROJECT_SUMMARY.md) - Architecture and design decisions

## 🗺️ Roadmap

### Completed ✅
- [x] Rich TUI interface with real-time metrics
- [x] Incremental backups with --link-dest
- [x] Backup rotation and retention
- [x] Logging system
- [x] Volume compression
- [x] Upload progress tracking
- [x] List remote backups command
- [x] Skip functionality (S key)
- [x] Help screen (H key)
- [x] Backup encryption (AES-256-GCM, RSA-4096)
- [x] Restore functionality
- [x] Management wrapper (bbman.py)
- [x] Real-time transfer metrics
- [x] GitHub key integration

### Planned
- [ ] Backup verification/checksums
- [ ] Email notifications
- [ ] Webhook support
- [ ] Backup scheduling (cron integration)
- [ ] Multi-server backup coordination
- [ ] Backup comparison/diff
- [ ] Web UI for backup management

## 📄 License

This project is part of the Linux Tools repository.

## 🤝 Contributing

This tool is designed to be extracted into its own GitHub repository. Contributions welcome!

## 🙏 Acknowledgments

- Built with [Rich](https://github.com/Textualize/rich) for beautiful terminal interfaces
- Uses [Click](https://github.com/pallets/click) for CLI framework
- Docker integration via [docker-py](https://github.com/docker/docker-py)

---

**Version:** 1.0.0  
**Last Updated:** 2026-01-15

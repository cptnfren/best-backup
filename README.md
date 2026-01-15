# bbackup - Docker Backup Tool

A comprehensive, feature-rich Docker backup solution with a beautiful Rich TUI interface. Backs up Docker containers, volumes, networks, and configurations with support for incremental backups, remote storage (Google Drive via rclone, SFTP), and intelligent rotation policies.

## Features

- 🎨 **Rich TUI Interface** - Beautiful terminal interface similar to BTOP
- 🐳 **Docker Integration** - Full Docker backup (containers, volumes, networks, metadata)
- 📦 **Hybrid Backup Strategy** - rsync for volumes (efficient), tar for metadata (structured)
- 🔄 **Incremental Backups** - Only backup changes using rsync `--link-dest`
- ☁️ **Remote Storage** - Google Drive (rclone), SFTP, local directories
- 🔁 **Backup Rotation** - Time-based retention with storage quota management ✅
- ⚙️ **Flexible Configuration** - YAML config files with CLI overrides
- 🎯 **Selective Backup** - Choose specific containers, volumes, or backup sets
- 📊 **Progress Visualization** - Real-time progress bars and status displays
- 📝 **Logging System** - File-based logging with rotation
- ⌨️ **Keyboard Controls** - Q (quit), P (pause), S (skip), H (help)

## Installation

### Prerequisites

- Python 3.8+
- Docker (with Docker socket access)
- rsync (for volume backups)
- rclone (optional, for Google Drive support)

### Install from Source

```bash
# Clone or navigate to the best-backup directory
cd best-backup

# Install dependencies
pip install -r requirements.txt

# Make CLI executable
chmod +x bbackup.py

# Install as system command (optional)
sudo ln -s $(pwd)/bbackup.py /usr/local/bin/bbackup
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Setup rclone (for Google Drive)

```bash
# Install rclone (if not already installed)
# See: https://rclone.org/install/

# Configure Google Drive remote
rclone config

# Test connection
rclone lsd gdrive:
```

## Quick Start

### 1. Initialize Configuration

```bash
bbackup init-config
```

This creates a configuration file at `~/.config/bbackup/config.yaml`.

### 2. Edit Configuration

Edit `~/.config/bbackup/config.yaml` to configure:
- Backup sets (groups of containers)
- Remote storage destinations
- Retention policies
- Compression settings

### 3. Run Backup

**Interactive Mode (default):**
```bash
bbackup backup
```

**Using Backup Set:**
```bash
bbackup backup --backup-set production
```

**Specific Containers:**
```bash
bbackup backup --containers dms minio npm
```

**Configuration Only (no volumes):**
```bash
bbackup backup --config-only
```

**Volumes Only:**
```bash
bbackup backup --volumes-only
```

**Incremental Backup:**
```bash
bbackup backup --incremental
```

## Configuration

### Configuration File Location

bbackup looks for configuration in this order:
1. `~/.config/bbackup/config.yaml`
2. `~/.bbackup/config.yaml`
3. `/etc/bbackup/config.yaml`
4. `./config.yaml` (current directory)

### Example Configuration

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
```

**Remote Storage:**
```yaml
remotes:
  gdrive:
    enabled: true
    type: rclone
    remote_name: gdrive
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

## Usage

### CLI Commands

```bash
# Create backup (interactive)
bbackup backup

# Create backup with specific containers
bbackup backup --containers dms minio

# Use backup set
bbackup backup --backup-set production

# Configuration only (no volumes)
bbackup backup --config-only

# Incremental backup
bbackup backup --incremental

# List containers
bbackup list-containers

# List backup sets
bbackup list-backup-sets

# List backups on remote storage
bbackup list-remote-backups --remote gdrive

# Initialize config
bbackup init-config
```

### CLI Options

```
Options:
  --containers, -C      Container names to backup (multiple)
  --backup-set, -s     Use predefined backup set
  --config-only        Backup only configurations
  --volumes-only       Backup only volumes
  --no-networks        Skip network backups
  --incremental, -i    Use incremental backup
  --remote, -r         Remote storage destinations (multiple)
  --no-interactive     Disable interactive mode
  --config, -c         Path to config file
```

## Backup Strategy

### Hybrid Approach

- **Volumes**: Backed up using `rsync` for efficiency with large files
  - Supports incremental backups via `--link-dest`
  - Handles sparse files and large datasets efficiently
  
- **Metadata**: Backed up using `tar` with compression
  - Container configurations (docker inspect)
  - Network configurations
  - Container logs
  - Backup metadata

### Incremental Backups

When `--incremental` is used or `incremental.enabled: true` in config:
- rsync uses `--link-dest` to reference previous backups ✅
- Only changed files are copied
- Unchanged files are hardlinked (saves space)
- Works best for volumes with large, slowly-changing data
- Automatically finds previous backup for each volume

## Remote Storage

### Google Drive (rclone)

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
       remote_name: gdrive  # Your rclone remote name
       path: /backups/docker
   ```

### SFTP

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

### Local Directory

```yaml
remotes:
  local:
    enabled: true
    type: local
    path: ~/backups/docker
```

## Backup Rotation

### Time-Based Retention ✅

- **Daily**: Keep N most recent daily backups
- **Weekly**: Keep N weekly backups (typically Sunday backups)
- **Monthly**: Keep N monthly backups (first of month)
- Automatically integrated into backup workflow

### Storage Quota Management ✅

When storage quota is configured:
- Warns when storage exceeds warning threshold
- Automatically cleans up old backups when cleanup threshold is reached ✅
- Deletes oldest backups first (configurable strategy)
- Runs automatically after each backup upload

## Project Structure

```
best-backup/
├── bbackup/              # Main package
│   ├── __init__.py
│   ├── cli.py           # CLI entry point
│   ├── config.py        # Configuration management
│   ├── docker_backup.py # Docker backup logic
│   ├── tui.py           # Rich TUI interface
│   ├── remote.py        # Remote storage integration
│   └── rotation.py      # Backup rotation logic
├── bbackup.py           # Main CLI script
├── config.yaml.example  # Example configuration
├── requirements.txt     # Python dependencies
├── README.md            # This file
└── setup.py             # Package setup (future)
```

## Development

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
```

## Troubleshooting

### Docker Permission Issues

```bash
# Add user to docker group
sudo usermod -aG docker $USER
# Log out and back in
```

### rclone Not Found

```bash
# Install rclone
# See: https://rclone.org/install/
```

### rsync Not Available

```bash
# Install rsync
sudo apt-get install rsync  # Debian/Ubuntu
sudo yum install rsync      # RHEL/CentOS
```

## License

This project is part of the Linux Tools repository.

## Contributing

This tool is designed to be extracted into its own GitHub repository. Contributions welcome!

## Roadmap

- [x] Restore functionality (✅ Implemented - see `docs/tests/TEST_RESULTS_COMPREHENSIVE.md`)
- [x] Incremental backups with --link-dest (✅ Implemented)
- [x] Backup rotation and retention (✅ Implemented)
- [x] Logging system (✅ Implemented)
- [x] Volume compression (✅ Implemented)
- [x] Upload progress tracking (✅ Implemented)
- [x] List remote backups (✅ Implemented - `list-remote-backups` command)
- [x] Skip functionality (✅ Implemented - 'S' key)
- [x] Help screen (✅ Implemented - 'H' key)
- [ ] Backup verification/checksums
- [ ] Email notifications
- [ ] Webhook support
- [ ] Backup scheduling (cron integration)
- [ ] Backup encryption
- [ ] Multi-server backup coordination

## Development Documentation

For development and technical documentation, see:
- **Development Reports:** `docs/reports/` - Deficiency reports, feature status, code analysis
- **Test Results:** `docs/tests/` - Test results and verification reports
- **Architecture:** `PROJECT_SUMMARY.md` - Design decisions and architecture

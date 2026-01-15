# bbackup Management Guide

**bbman** - Universal wrapper script for managing bbackup application lifecycle.

## Overview

`bbman.py` is a comprehensive management wrapper that provides:
- First-run detection and interactive setup
- File-level version checking with Git-compatible checksums
- Repository URL management with override support
- Health diagnostics and dependency checking
- Backup status and cleanup utilities
- Application launcher

## Installation

The `bbman.py` script is located at the root of the repository. Make it executable:

```bash
chmod +x bbman.py
```

Or run directly:
```bash
python3 bbman.py --help
```

## Commands

### Setup

```bash
bbman setup
```

Run interactive setup wizard for first-time configuration:
- Checks Docker access
- Verifies system dependencies (rsync, tar, etc.)
- Checks Python packages
- Creates configuration file
- Optional encryption key setup

### Health Check

```bash
bbman health
```

Run comprehensive health check:
- Docker daemon accessibility
- Docker socket permissions
- System tools (rsync, tar, rclone)
- Python dependencies
- Configuration file validity
- Directory permissions

### Dependency Management

```bash
bbman check-deps
bbman check-deps --install  # Install missing packages
```

Check and optionally install missing dependencies:
- System tools (docker, rsync, tar, rclone)
- Python packages from requirements.txt
- Install missing packages with confirmation

### Configuration Validation

```bash
bbman validate-config
```

Validate configuration file:
- Parse YAML syntax
- Check required fields
- Verify paths and permissions
- Display configuration summary

### Backup Status

```bash
bbman status
```

Show backup status and history:
- Total backups count
- Total size
- Encrypted backups count
- Recent backups list

### Cleanup

```bash
bbman cleanup
bbman cleanup --staging-days 7 --log-days 30
bbman cleanup --yes  # Skip confirmation
```

Cleanup old files:
- Staging files (default: keep 7 days)
- Log files (default: keep 30 days)
- Old backups (per retention policy)
- Temporary files

### Diagnostics

```bash
bbman diagnostics
bbman diagnostics --output report.txt
```

Run diagnostics and generate report:
- System information
- Docker version and status
- Python environment
- Configuration summary
- Recent errors from logs

### Version Management

```bash
bbman check-updates
bbman check-updates --branch main
bbman update
bbman update --method git
bbman update --method download --yes
```

Check for updates using file-level checksums:
- Compares local vs. remote file checksums (SHA-256)
- Shows which files have changed
- Updates via Git pull or direct download
- Verifies checksums after update
- Creates backup before updating

### Repository URL Management

```bash
bbman repo-url              # Show current URL
bbman repo-url --url URL    # Set override URL
```

Manage repository URL:
- Shows current repository URL (with override source)
- Set override via command
- Override priority:
  1. Environment variable: `BBACKUP_REPO_URL`
  2. Config file: `~/.config/bbackup/management.yaml`
  3. Hard-coded default in `bbman.py`

### Application Launcher

```bash
bbman run backup --containers my_container
bbman run list-containers
bbman run restore --backup-path /path/to/backup
```

Launch main bbackup application:
- Passes through all arguments
- Can be used as direct replacement for `bbackup.py`
- Optional pre-flight checks

## Repository URL Override

### Environment Variable

```bash
export BBACKUP_REPO_URL="https://github.com/owner/repo"
bbman check-updates
```

### Config File

Edit `~/.config/bbackup/management.yaml`:

```yaml
repo_url: "https://github.com/owner/repo"
auto_check_updates: true
check_interval_days: 7
auto_setup_on_first_run: true
health_check_before_run: false
update_method: "git"  # git, download, manual
```

### Supported Repository Types

- **GitHub**: `https://github.com/{owner}/{repo}`
- **GitLab**: `https://gitlab.com/{owner}/{repo}`
- **Custom HTTP**: `https://example.com/repo` (must provide API/manifest)

## File-Level Version Checking

The version checking system uses SHA-256 checksums (Git-compatible) to compare files:

1. **Local Checksums**: Computed for all tracked files (`.py`, `.yaml`, `.md`, etc.)
2. **Remote Checksums**: Fetched from repository via:
   - GitHub/GitLab API (Git tree)
   - VERSION_MANIFEST.json file
   - Direct file download (fallback)
3. **Comparison**: File-by-file comparison to detect changes
4. **Update**: Downloads only changed files, verifies checksums

## First Run Detection

The system detects first run by checking:
- Config file existence: `~/.config/bbackup/config.yaml`
- First-run marker: `~/.local/share/bbackup/.first_run_complete`

If either is missing, the setup wizard is triggered automatically (or can be run manually with `bbman setup`).

## Management Configuration

Configuration file: `~/.config/bbackup/management.yaml`

**Settings:**
- `repo_url`: Repository URL override (optional)
- `auto_check_updates`: Check for updates automatically (default: true)
- `check_interval_days`: Days between update checks (default: 7)
- `auto_setup_on_first_run`: Run setup wizard on first run (default: true)
- `health_check_before_run`: Run health check before launching app (default: false)
- `update_method`: Update method - "git", "download", or "manual" (default: "git")

## Examples

### Complete Setup Flow

```bash
# First time setup
bbman setup

# Check system health
bbman health

# Check dependencies
bbman check-deps --install

# Validate configuration
bbman validate-config

# Run backup
bbman run backup --containers my_container
```

### Update Workflow

```bash
# Check for updates
bbman check-updates

# Update if available
bbman update --yes

# Verify after update
bbman health
```

### Maintenance

```bash
# Check backup status
bbman status

# Cleanup old files
bbman cleanup --yes

# Run diagnostics
bbman diagnostics --output diagnostics.txt
```

## Troubleshooting

### First Run Issues

If setup wizard doesn't run automatically:
```bash
bbman setup
```

### Update Failures

If updates fail:
1. Check repository URL: `bbman repo-url`
2. Verify network access
3. Check logs: `~/.local/share/bbackup/bbackup.log`
4. Run diagnostics: `bbman diagnostics`

### Health Check Failures

If health check shows issues:
1. Fix Docker access (add user to docker group)
2. Install missing dependencies: `bbman check-deps --install`
3. Validate config: `bbman validate-config`

## Integration with bbackup

The wrapper seamlessly integrates with the main application:

```bash
# These are equivalent:
bbman run backup --containers my_container
python3 bbackup.py backup --containers my_container

# Wrapper adds management features:
bbman health          # Not available in bbackup.py
bbman check-updates   # Not available in bbackup.py
bbman setup           # Not available in bbackup.py
```

## Security Considerations

- Repository URL override allows using custom/private repositories
- Checksums verified before and after updates
- HTTPS-only for repository access
- Backup created before updates
- File path validation prevents directory traversal

---

**See Also:**
- [README.md](../README.md) - Main documentation
- [QUICKSTART.md](../QUICKSTART.md) - Quick start guide
- [QUICK_INSTALL.md](../QUICK_INSTALL.md) - Installation guide

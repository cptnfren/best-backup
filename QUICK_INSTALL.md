# Quick Installation Guide

## Using Management Wrapper (Recommended)

The `bbman.py` wrapper provides easy setup and management:

```bash
# Make executable
chmod +x bbman.py

# Run setup wizard (checks dependencies, creates config)
python3 bbman.py setup

# Launch application
python3 bbman.py run backup --containers my_container
```

The setup wizard automatically:
- Checks Docker access
- Verifies system dependencies (rsync, tar, rclone)
- Checks Python packages
- Creates configuration file
- Optionally sets up encryption keys

## Running bbackup Without Installation

You can run bbackup directly without installing it:

```bash
# From the best-backup directory
python3 bbackup.py init-encryption --method asymmetric

# Or using Python module syntax
python3 -m bbackup.cli init-encryption --method asymmetric

# Or using management wrapper
python3 bbman.py run init-encryption --method asymmetric
```

## Installing bbackup as System Command

### Option 1: Install via pip (Recommended)

```bash
cd best-backup

# Development mode (editable, changes take effect immediately)
pip3 install -e .

# Or normal install (copies files)
pip3 install .
```

This installs both `bbackup` and `bbman` as system commands available everywhere.

**Verify installation:**
```bash
which bbackup
which bbman
bbackup --version
bbman --version
```

### Option 2: Create Symlink (Quick)

```bash
cd best-backup
sudo ln -s $(pwd)/bbackup.py /usr/local/bin/bbackup
chmod +x bbackup.py
```

### Option 3: Add to PATH

```bash
# Add to ~/.bashrc or ~/.zshrc
export PATH="$PATH:/path/to/best-backup"

# Then make executable
chmod +x /path/to/best-backup/bbackup.py
```

## Verify Installation

```bash
# Check if command is available
which bbackup

# Test command
bbackup --version
bbackup --help
```

## Common Commands

```bash
# Initialize encryption keys
bbackup init-encryption --method asymmetric

# Initialize config
bbackup init-config

# Run backup
bbackup backup --containers my_container

# List containers
bbackup list-containers
```

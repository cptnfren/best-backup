# Installation Guide - System Command Registration

This guide explains how to install bbackup so it's available as a system command from anywhere.

## Quick Install (Recommended)

The easiest way to install bbackup as a system command:

```bash
# Navigate to the repository
cd best-backup

# Install in development mode (editable, changes take effect immediately)
pip3 install -e .

# Or install normally (copies files)
pip3 install .
```

After installation, both commands are available system-wide:
- `bbackup` - Main backup application
- `bbman` - Management wrapper

## Verify Installation

```bash
# Check if commands are available
which bbackup
which bbman

# Test commands
bbackup --version
bbackup --help

bbman --version
bbman --help
```

## Installation Methods

### Method 1: pip install (Recommended)

**Development Mode (Editable):**
```bash
pip3 install -e .
```
- Installs as system command
- Changes to source code take effect immediately
- Best for development

**Normal Install:**
```bash
pip3 install .
```
- Installs as system command
- Copies files to site-packages
- Best for production

**User Install (No sudo required):**
```bash
pip3 install --user -e .
```
- Installs to user directory (`~/.local/bin`)
- No sudo required
- May need to add `~/.local/bin` to PATH

### Method 2: Create Symlinks (Quick, No Installation)

```bash
# Make scripts executable
chmod +x bbackup.py bbman.py

# Create symlinks in /usr/local/bin (requires sudo)
sudo ln -s $(pwd)/bbackup.py /usr/local/bin/bbackup
sudo ln -s $(pwd)/bbman.py /usr/local/bin/bbman
```

**Or for user-only (no sudo):**
```bash
# Create ~/bin if it doesn't exist
mkdir -p ~/bin

# Create symlinks
ln -s $(pwd)/bbackup.py ~/bin/bbackup
ln -s $(pwd)/bbman.py ~/bin/bbman

# Add to PATH (add to ~/.bashrc or ~/.zshrc)
export PATH="$HOME/bin:$PATH"
```

### Method 3: Add to PATH

```bash
# Add to ~/.bashrc or ~/zshrc
export PATH="$PATH:/path/to/best-backup"

# Make scripts executable
chmod +x /path/to/best-backup/bbackup.py
chmod +x /path/to/best-backup/bbman.py

# Reload shell
source ~/.bashrc  # or source ~/.zshrc
```

## Launch Commands

Once installed, you can launch from anywhere:

```bash
# Main backup application
bbackup backup
bbackup list-containers
bbackup restore --backup-path /path/to/backup --all

# Management wrapper
bbman setup
bbman health
bbman run backup --containers my_container
```

## Uninstall

If installed via pip:

```bash
pip3 uninstall bbackup
```

If installed via symlinks:

```bash
sudo rm /usr/local/bin/bbackup
sudo rm /usr/local/bin/bbman
```

## Troubleshooting

### Command Not Found

If `bbackup` or `bbman` commands are not found:

1. **Check if installed:**
   ```bash
   pip3 show bbackup
   ```

2. **Check PATH:**
   ```bash
   echo $PATH
   which bbackup
   ```

3. **Reinstall:**
   ```bash
   pip3 install -e . --force-reinstall
   ```

### Permission Denied

If you get permission errors:

1. **Use user install:**
   ```bash
   pip3 install --user -e .
   ```

2. **Or use sudo:**
   ```bash
   sudo pip3 install -e .
   ```

3. **Or fix permissions:**
   ```bash
   sudo chmod +x bbackup.py bbman.py
   ```

### Python Version Issues

Ensure Python 3.8+ is used:

```bash
# Check Python version
python3 --version

# Use specific Python version if needed
python3.8 -m pip install -e .
```

## Post-Installation Setup

After installation, run the setup wizard:

```bash
bbman setup
```

This will:
- Check Docker access
- Verify dependencies
- Create configuration file
- Set up encryption keys (optional)

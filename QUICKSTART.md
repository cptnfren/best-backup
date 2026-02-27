# Quick start guide

> Get from zero to a completed backup in about 5 minutes.

---

## Step 1: Install

```bash
git clone https://github.com/YOUR_USERNAME/best-backup.git
cd best-backup
pip install -e .
```

This registers both `bbackup` and `bbman` as system commands.

---

## Step 2: First-time setup

```bash
bbman setup
```

The setup wizard checks Docker access, verifies system dependencies (`rsync`, `tar`), installs any missing Python packages, and creates a starter config at `~/.config/bbackup/config.yaml`.

If you prefer to do this manually:

```bash
bbackup init-config
```

---

## Step 3: Edit your config

Open `~/.config/bbackup/config.yaml` and define which containers you want to back up and where to store the results.

```yaml
backup:
  local_staging: /tmp/bbackup_staging
  backup_sets:
    production:
      description: "Production stack"
      containers:
        - myapp
        - mydb
      scope:
        volumes: true
        configs: true

remotes:
  local:
    enabled: true
    type: local
    path: ~/backups/docker
```

A fully annotated example with all options is in [`config.yaml.example`](config.yaml.example).

---

## Step 4: Run your first backup

```bash
bbackup backup
```

You'll get an interactive container picker, then a live dashboard showing transfer speed, bytes moved, and per-container status as the backup runs.

To skip the picker and go straight to a specific set:

```bash
bbackup backup --backup-set production
```

Or target individual containers directly:

```bash
bbackup backup --containers myapp mydb
```

---

## Common scenarios

### Backup only configs (no volume data)

```bash
bbackup backup --config-only
```

### Incremental backup (only changed data)

```bash
bbackup backup --incremental
```

Uses rsync `--link-dest` so unchanged files are hardlinked from the previous backup rather than copied. Works well for large volumes that change slowly.

### Send to Google Drive

1. Configure rclone first:
   ```bash
   rclone config
   # Create a remote named "gdrive"
   ```

2. Add to your config:
   ```yaml
   remotes:
     gdrive:
       enabled: true
       type: rclone
       remote_name: gdrive
       path: /backups/docker
   ```

3. Run:
   ```bash
   bbackup backup --remote gdrive
   ```

### Restore from a backup

```bash
bbackup restore --backup-path ~/backups/docker/backup_2026-02-26 --all
```

Restore specific containers only:

```bash
bbackup restore --backup-path ~/backups/docker/backup_2026-02-26 --containers myapp
```

---

## Troubleshooting

**"Permission denied" on Docker socket**

```bash
sudo usermod -aG docker $USER
newgrp docker
```

**`rsync` not found**

```bash
sudo apt-get install rsync      # Debian / Ubuntu
sudo yum install rsync          # RHEL / CentOS
```

**`rclone` not found**

```bash
curl https://rclone.org/install.sh | sudo bash
```

**Config not found**

```bash
bbackup init-config
# or
bbman setup
```

---

## Next steps

- [README.md](README.md) - Full CLI reference and feature list
- [INSTALL.md](INSTALL.md) - Alternative installation methods
- [docs/management.md](docs/management.md) - Full `bbman` reference
- [docs/encryption.md](docs/encryption.md) - Encryption setup
- [`config.yaml.example`](config.yaml.example) - All configuration options

# bbackup Quick Start Guide

## 5-Minute Setup

### Step 1: Install Dependencies

```bash
# Install Python packages
pip3 install -r requirements.txt

# Ensure rsync is installed
sudo apt-get install rsync  # Debian/Ubuntu
# or
sudo yum install rsync      # RHEL/CentOS
```

### Step 2: Initialize Configuration

```bash
# Create config file
./bbackup.py init-config

# Or if installed system-wide:
bbackup init-config
```

### Step 3: Edit Configuration

Edit `~/.config/bbackup/config.yaml`:

```yaml
# Minimal working config
backup:
  local_staging: /tmp/bbackup_staging
  backup_sets:
    my_containers:
      description: "My containers"
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

### Step 4: Run Your First Backup

```bash
# Interactive mode (select containers from menu)
./bbackup.py backup

# Or backup specific containers
./bbackup.py backup --containers container1 container2

# Or use a backup set
./bbackup.py backup --backup-set my_containers
```

## Common Use Cases

### Backup All Containers

```bash
bbackup backup
# Select "all" when prompted
```

### Backup Only Configurations (No Data)

```bash
bbackup backup --config-only
```

### Backup Only Volumes (No Configs)

```bash
bbackup backup --volumes-only
```

### Incremental Backup

```bash
bbackup backup --incremental
```

### Backup to Google Drive

1. Setup rclone:
   ```bash
   rclone config
   # Create remote named "gdrive"
   ```

2. Edit config:
   ```yaml
   remotes:
     gdrive:
       enabled: true
       type: rclone
       remote_name: gdrive
       path: /backups/docker
   ```

3. Run backup:
   ```bash
   bbackup backup --remote gdrive
   ```

## Troubleshooting

### "Docker not found" Error

```bash
# Add user to docker group
sudo usermod -aG docker $USER
# Log out and back in, or:
newgrp docker
```

### "rclone not found" Error

Install rclone:
```bash
# See: https://rclone.org/install/
curl https://rclone.org/install.sh | sudo bash
```

### Permission Denied

```bash
# Make script executable
chmod +x bbackup.py

# Or run with Python
python3 bbackup.py backup
```

## Next Steps

- Read the full [README.md](README.md) for advanced features
- Configure backup sets for different container groups
- Set up retention policies
- Configure multiple remote destinations

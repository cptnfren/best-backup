# Implementation Roadmap - bbackup

**Based on Deficiency Analysis**  
**Generated:** 2026-01-08

---

## Phase 1: Critical Fixes (Week 1-2)

### 1.1 Implement Incremental Backups
**Priority:** 🔴 Critical  
**Effort:** Medium (2-3 days)

**Tasks:**
- [ ] Modify `backup_volume()` to use `--link-dest` when `incremental=True`
- [ ] Call `_find_previous_volume_backup()` to locate previous backup
- [ ] Add `--link-dest` argument to rsync command
- [ ] Test with actual volume backups
- [ ] Update documentation if needed

**Files to Modify:**
- `bbackup/docker_backup.py:backup_volume()` (lines 99-193)

**Code Changes:**
```python
# In backup_volume(), when incremental=True:
if incremental:
    prev_backup = self._find_previous_volume_backup(volume_name, backup_dir.parent)
    if prev_backup:
        rsync_cmd.extend(["--link-dest", str(prev_backup)])
```

---

### 1.2 Integrate Backup Rotation
**Priority:** 🔴 Critical  
**Effort:** Medium (2-3 days)

**Tasks:**
- [ ] Instantiate `BackupRotation` in `BackupRunner`
- [ ] Call rotation checks after successful uploads
- [ ] Integrate storage quota checking
- [ ] Trigger automatic cleanup when thresholds exceeded
- [ ] Test rotation logic with multiple backups
- [ ] Add rotation status to TUI

**Files to Modify:**
- `bbackup/backup_runner.py` (add rotation integration)
- `bbackup/tui.py` (add rotation status display)

**Code Changes:**
```python
# In backup_runner.py, after upload_to_remotes():
from .rotation import BackupRotation

# In __init__:
self.rotation = BackupRotation(config.retention)

# After upload:
for remote in remotes:
    quota_status = self.rotation.check_storage_quota(remote, remote_path)
    if quota_status["cleanup_needed"]:
        backups = self.remote_mgr.list_backups(remote)
        to_keep, to_delete = self.rotation.filter_backups_by_retention(backups, remote_path)
        self.rotation.cleanup_old_backups(remote, remote_path, to_delete)
```

---

### 1.3 Implement Logging System
**Priority:** 🔴 Critical  
**Effort:** Medium (2-3 days)

**Tasks:**
- [ ] Add Python `logging` module setup
- [ ] Implement file logging with rotation
- [ ] Use config settings (level, file, max_size_mb, backup_count)
- [ ] Add logging to all major operations
- [ ] Log errors, warnings, and info messages
- [ ] Test log rotation

**Files to Create/Modify:**
- Create `bbackup/logging.py` (new file)
- Modify all modules to use logger

**Code Structure:**
```python
# bbackup/logging.py
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from .config import Config

def setup_logging(config: Config):
    logger = logging.getLogger('bbackup')
    logger.setLevel(getattr(logging, config.data.get('logging', {}).get('level', 'INFO')))
    
    log_file = Path(config.data.get('logging', {}).get('file', '~/.local/share/bbackup/bbackup.log'))
    log_file = Path(log_file).expanduser()
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    handler = RotatingFileHandler(
        log_file,
        maxBytes=config.data.get('logging', {}).get('max_size_mb', 10) * 1024 * 1024,
        backupCount=config.data.get('logging', {}).get('backup_count', 5)
    )
    logger.addHandler(handler)
    return logger
```

---

### 1.4 Add Volume Compression
**Priority:** 🔴 Critical  
**Effort:** Low (1 day)

**Tasks:**
- [ ] Apply compression to volume backups
- [ ] Use tar.gz or similar for compressed volumes
- [ ] Respect compression config settings
- [ ] Test with large volumes

**Files to Modify:**
- `bbackup/docker_backup.py:backup_volume()`

**Code Changes:**
```python
# After volume backup, if compression enabled:
compression = self.config.data.get("backup", {}).get("compression", {})
if compression.get("enabled", False):
    # Create compressed tar archive of volume
    tar_file = backup_dir / "volumes" / f"{volume_name}.tar.gz"
    with tarfile.open(tar_file, "w:gz") as tar:
        tar.add(volume_backup_dir, arcname=volume_name)
    # Remove uncompressed directory
    shutil.rmtree(volume_backup_dir)
```

---

## Phase 2: Medium Priority (Week 3-4)

### 2.1 Connect Upload Progress to TUI
**Priority:** 🟡 Medium  
**Effort:** Low (1 day)

**Tasks:**
- [ ] Parse rclone progress output
- [ ] Update `BackupStatus` with upload progress
- [ ] Display progress in TUI during uploads

**Files to Modify:**
- `bbackup/backup_runner.py:upload_to_remotes()`
- `bbackup/remote.py:upload_to_rclone()`

---

### 2.2 Add Remote Backup Listing
**Priority:** 🟡 Medium  
**Effort:** Low (1 day)

**Tasks:**
- [ ] Create `list-remote-backups` CLI command
- [ ] Use `RemoteStorageManager.list_backups()`
- [ ] Display backups from remote storage

**Files to Modify:**
- `bbackup/cli.py` (add new command)

---

### 2.3 Implement Skip Functionality
**Priority:** 🟡 Medium  
**Effort:** Low (1 day)

**Tasks:**
- [ ] Add skip flag to `BackupStatus`
- [ ] Handle 'S' key in TUI
- [ ] Implement skip logic in backup runner

**Files to Modify:**
- `bbackup/tui.py:run_with_live_dashboard()`
- `bbackup/backup_runner.py:run_backup()`

---

### 2.4 Add Help Screen
**Priority:** 🟡 Medium  
**Effort:** Low (1 day)

**Tasks:**
- [ ] Create help panel in TUI
- [ ] Show keyboard shortcuts
- [ ] Display usage information
- [ ] Handle 'H' key

**Files to Modify:**
- `bbackup/tui.py` (add help panel)

---

## Phase 3: Low Priority (Week 5-6)

### 3.1 Apply Docker Timeout
**Priority:** 🟢 Low  
**Effort:** Very Low (2 hours)

**Tasks:**
- [ ] Apply `docker.timeout` config to Docker client
- [ ] Test timeout behavior

**Files to Modify:**
- `bbackup/docker_backup.py:__init__()`

---

### 3.2 Add Backup Verification
**Priority:** 🟢 Low  
**Effort:** Medium (2-3 days)

**Tasks:**
- [ ] Generate checksums during backup
- [ ] Store checksums in metadata
- [ ] Create `verify-backup` command
- [ ] Verify backup integrity

**Files to Create/Modify:**
- Create `bbackup/verification.py` (new file)
- Modify `bbackup/cli.py` (add verify command)

---

### 3.3 Improve Error Recovery
**Priority:** 🟢 Low  
**Effort:** Medium (2-3 days)

**Tasks:**
- [ ] Add retry logic for failed operations
- [ ] Implement resume for interrupted backups
- [ ] Better error messages

**Files to Modify:**
- `bbackup/backup_runner.py`
- `bbackup/docker_backup.py`

---

## Phase 4: Future Enhancements (Roadmap)

### 4.1 Email Notifications
**Priority:** 🔵 Future  
**Effort:** Medium (2-3 days)

**Tasks:**
- [ ] Add email notification support
- [ ] Configure SMTP settings
- [ ] Send backup status emails

---

### 4.2 Webhook Support
**Priority:** 🔵 Future  
**Effort:** Low (1 day)

**Tasks:**
- [ ] Add webhook notification support
- [ ] POST backup status to webhook URL

---

### 4.3 Backup Scheduling
**Priority:** 🔵 Future  
**Effort:** Medium (2-3 days)

**Tasks:**
- [ ] Add cron integration
- [ ] Schedule backups from config
- [ ] Create systemd timer option

---

### 4.4 Backup Encryption
**Priority:** 🔵 Future  
**Effort:** Medium (3-4 days)

**Tasks:**
- [ ] Add encryption support
- [ ] Use GPG or similar
- [ ] Encrypt sensitive backups

---

## Estimated Timeline

- **Phase 1 (Critical):** 2 weeks
- **Phase 2 (Medium):** 2 weeks
- **Phase 3 (Low):** 2 weeks
- **Phase 4 (Future):** Ongoing

**Total for Phases 1-3:** ~6 weeks

---

## Success Criteria

### Phase 1 Complete When:
- ✅ Incremental backups work with `--link-dest`
- ✅ Backup rotation automatically cleans up old backups
- ✅ Logging system writes to files with rotation
- ✅ Volume backups are compressed

### Phase 2 Complete When:
- ✅ Upload progress shown in TUI
- ✅ Can list backups from remote storage
- ✅ Skip functionality works
- ✅ Help screen accessible

### Phase 3 Complete When:
- ✅ Docker timeout applied
- ✅ Backup verification works
- ✅ Better error recovery implemented

---

## Testing Requirements

Each phase should include:
- Unit tests for new functionality
- Integration tests for workflows
- Manual testing with real Docker containers
- Documentation updates

---

**Last Updated:** 2026-01-08

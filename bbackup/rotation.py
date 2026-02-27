"""
Backup rotation and retention management.
Handles time-based retention and storage quota management.
"""

import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from rich.console import Console

from .config import RetentionPolicy, RemoteStorage


class BackupRotation:
    """Manage backup rotation and retention."""
    
    def __init__(self, retention: RetentionPolicy, console: Console = None):
        self.retention = retention
        self.console = console or Console()
    
    def get_backup_age_category(self, backup_date: datetime) -> str:
        """Categorize backup by age."""
        now = datetime.now()
        age = now - backup_date
        
        if age.days == 0:
            return "daily"
        elif age.days < 7:
            return "daily"
        elif age.days < 30:
            return "weekly"
        else:
            return "monthly"
    
    def should_keep_backup(self, backup_date: datetime) -> bool:
        """Determine if backup should be kept based on retention policy."""
        category = self.get_backup_age_category(backup_date)
        
        if category == "daily":
            # Keep if within daily retention period
            return True  # Will be filtered by count
        elif category == "weekly":
            # Keep if it's a weekly backup (e.g., Sunday)
            return backup_date.weekday() == 6  # Sunday
        elif category == "monthly":
            # Keep if it's the first of the month
            return backup_date.day == 1
        
        return True
    
    def filter_backups_by_retention(
        self,
        backups: List[Dict],
        remote_path: Path,
    ) -> tuple[List[Dict], List[Dict]]:
        """Filter backups to keep vs delete based on retention policy."""
        # Parse backup dates from names or metadata
        backup_list = []
        for backup in backups:
            backup_date = self._parse_backup_date(backup)
            if backup_date:
                backup_list.append({
                    "name": backup,
                    "date": backup_date,
                    "path": remote_path / backup,
                })
        
        # Sort by date (newest first)
        backup_list.sort(key=lambda x: x["date"], reverse=True)
        
        # Categorize backups
        daily_backups = []
        weekly_backups = []
        monthly_backups = []
        
        for backup in backup_list:
            category = self.get_backup_age_category(backup["date"])
            if category == "daily":
                daily_backups.append(backup)
            elif category == "weekly":
                weekly_backups.append(backup)
            elif category == "monthly":
                monthly_backups.append(backup)
        
        # Select backups to keep
        to_keep = []
        
        # Keep daily backups (up to retention limit)
        to_keep.extend(daily_backups[:self.retention.daily])
        
        # Keep weekly backups (up to retention limit)
        to_keep.extend(weekly_backups[:self.retention.weekly])
        
        # Keep monthly backups (up to retention limit)
        to_keep.extend(monthly_backups[:self.retention.monthly])
        
        # Determine what to delete
        to_delete = [b for b in backup_list if b not in to_keep]
        
        return [b["name"] for b in to_keep], [b["name"] for b in to_delete]
    
    def _parse_backup_date(self, backup_name: str) -> Optional[datetime]:
        """Parse backup date from backup name."""
        # Expected format: backup_YYYYMMDD_HHMMSS or similar
        try:
            # Try to extract date from name
            parts = backup_name.split("_")
            for part in parts:
                if len(part) == 8 and part.isdigit():  # YYYYMMDD
                    year = int(part[:4])
                    month = int(part[4:6])
                    day = int(part[6:8])
                    return datetime(year, month, day)
        except (ValueError, IndexError):
            pass
        
        # Fallback: use file modification time
        return None
    
    def check_storage_quota(
        self,
        remote: RemoteStorage,
        remote_path: Path,
    ) -> Dict[str, any]:
        """Check storage quota and return status."""
        if self.retention.max_storage_gb == 0:
            return {
                "enabled": False,
                "used_gb": 0,
                "max_gb": 0,
                "percent": 0,
                "warning": False,
                "cleanup_needed": False,
            }
        
        # Calculate used storage
        used_bytes = self._calculate_storage_usage(remote, remote_path)
        used_gb = used_bytes / (1024 ** 3)
        max_gb = self.retention.max_storage_gb
        percent = (used_gb / max_gb) * 100 if max_gb > 0 else 0
        
        return {
            "enabled": True,
            "used_gb": used_gb,
            "max_gb": max_gb,
            "percent": percent,
            "warning": percent >= self.retention.warning_threshold_percent,
            "cleanup_needed": percent >= self.retention.cleanup_threshold_percent,
        }
    
    def _calculate_storage_usage(self, remote: RemoteStorage, remote_path: Path) -> int:
        """Calculate total storage usage for remote."""
        if remote.type == "local":
            return self._calculate_local_storage(remote_path)
        elif remote.type == "rclone":
            return self._calculate_rclone_storage(remote)
        else:
            return 0
    
    def _calculate_local_storage(self, path: Path) -> int:
        """Calculate storage for local directory."""
        total = 0
        if path.exists():
            for item in path.rglob("*"):
                if item.is_file():
                    total += item.stat().st_size
        return total
    
    def _calculate_rclone_storage(self, remote: RemoteStorage) -> int:
        """Calculate storage for rclone remote."""
        if not remote.remote_name:
            return 0
        
        try:
            import subprocess
            cmd = ["rclone", "size", f"{remote.remote_name}:{remote.path}", "--json"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                return data.get("bytes", 0)
        except Exception:
            pass
        
        return 0
    
    def cleanup_old_backups(
        self,
        remote: RemoteStorage,
        remote_path: Path,
        backups_to_delete: List[str],
    ) -> int:
        """Delete old backups from remote storage."""
        deleted_count = 0
        
        for backup_name in backups_to_delete:
            if self._delete_backup(remote, remote_path, backup_name):
                deleted_count += 1
        
        return deleted_count
    
    def _delete_backup(self, remote: RemoteStorage, remote_path: Path, backup_name: str) -> bool:
        """Delete a single backup from remote."""
        if remote.type == "local":
            backup_path = remote_path / backup_name
            if backup_path.exists():
                import shutil
                shutil.rmtree(backup_path)
                return True
        elif remote.type == "rclone":
            try:
                import subprocess
                cmd = ["rclone", "purge", f"{remote.remote_name}:{remote.path}/{backup_name}"]
                result = subprocess.run(cmd, capture_output=True, text=True, check=False)
                return result.returncode == 0
            except Exception:
                pass
        
        return False

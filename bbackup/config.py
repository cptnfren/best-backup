"""
Configuration management for bbackup.
Handles loading and merging of YAML config files with CLI overrides.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class BackupScope:
    """Backup scope configuration."""
    containers: bool = True
    volumes: bool = True
    networks: bool = True
    configs: bool = True


@dataclass
class BackupSet:
    """Backup set definition."""
    name: str
    description: str = ""
    containers: List[str] = field(default_factory=list)
    scope: BackupScope = field(default_factory=BackupScope)


@dataclass
class RemoteStorage:
    """Remote storage configuration."""
    name: str
    enabled: bool = False
    type: str = "local"  # local, rclone, sftp
    path: str = ""
    compression: bool = True
    # SFTP specific
    host: Optional[str] = None
    port: int = 22
    user: Optional[str] = None
    key_file: Optional[str] = None
    # rclone specific
    remote_name: Optional[str] = None


@dataclass
class RetentionPolicy:
    """Backup retention policy."""
    daily: int = 7
    weekly: int = 4
    monthly: int = 12
    max_storage_gb: int = 0
    warning_threshold_percent: int = 80
    cleanup_threshold_percent: int = 90
    cleanup_strategy: str = "oldest_first"


@dataclass
class IncrementalSettings:
    """Incremental backup settings."""
    enabled: bool = True
    use_link_dest: bool = True
    min_file_size: int = 1048576  # 1MB


class Config:
    """Main configuration class."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._find_config()
        self.data: Dict[str, Any] = {}
        self.backup_sets: Dict[str, BackupSet] = {}
        self.remotes: Dict[str, RemoteStorage] = {}
        self.retention = RetentionPolicy()
        self.incremental = IncrementalSettings()
        self.scope = BackupScope()
        
        if self.config_path and os.path.exists(self.config_path):
            self.load()
        else:
            self._load_defaults()
    
    def _find_config(self) -> Optional[str]:
        """Find configuration file in standard locations."""
        config_locations = [
            os.path.expanduser("~/.config/bbackup/config.yaml"),
            os.path.expanduser("~/.bbackup/config.yaml"),
            "/etc/bbackup/config.yaml",
            os.path.join(os.getcwd(), "config.yaml"),
        ]
        
        for path in config_locations:
            if os.path.exists(path):
                return path
        
        return None
    
    def _load_defaults(self):
        """Load default configuration."""
        self.data = {
            "backup": {
                "local_staging": "/tmp/bbackup_staging",
                "compression": {"enabled": True, "level": 6, "format": "gzip"},
                "default_scope": {
                    "containers": True,
                    "volumes": True,
                    "networks": True,
                    "configs": True,
                },
            },
            "retention": {
                "daily": 7,
                "weekly": 4,
                "monthly": 12,
                "max_storage_gb": 0,
            },
            "incremental": {
                "enabled": True,
                "use_link_dest": True,
            },
        }
        self._parse_config()
    
    def load(self):
        """Load configuration from file."""
        try:
            with open(self.config_path, 'r') as f:
                self.data = yaml.safe_load(f) or {}
            self._parse_config()
        except Exception as e:
            raise ValueError(f"Failed to load config from {self.config_path}: {e}")
    
    def _parse_config(self):
        """Parse loaded configuration into dataclasses."""
        # Parse backup scope
        if "backup" in self.data:
            backup = self.data["backup"]
            if "default_scope" in backup:
                scope = backup["default_scope"]
                self.scope = BackupScope(
                    containers=scope.get("containers", True),
                    volumes=scope.get("volumes", True),
                    networks=scope.get("networks", True),
                    configs=scope.get("configs", True),
                )
        
        # Parse backup sets
        if "backup" in self.data and "backup_sets" in self.data["backup"]:
            for name, set_data in self.data["backup"]["backup_sets"].items():
                scope_data = set_data.get("scope", {})
                scope = BackupScope(
                    containers=scope_data.get("containers", True),
                    volumes=scope_data.get("volumes", True),
                    networks=scope_data.get("networks", True),
                    configs=scope_data.get("configs", True),
                )
                self.backup_sets[name] = BackupSet(
                    name=name,
                    description=set_data.get("description", ""),
                    containers=set_data.get("containers", []),
                    scope=scope,
                )
        
        # Parse remote storage
        if "remotes" in self.data:
            for name, remote_data in self.data["remotes"].items():
                self.remotes[name] = RemoteStorage(
                    name=name,
                    enabled=remote_data.get("enabled", False),
                    type=remote_data.get("type", "local"),
                    path=remote_data.get("path", ""),
                    compression=remote_data.get("compression", True),
                    host=remote_data.get("host"),
                    port=remote_data.get("port", 22),
                    user=remote_data.get("user"),
                    key_file=remote_data.get("key_file"),
                    remote_name=remote_data.get("remote_name"),
                )
        
        # Parse retention policy
        if "retention" in self.data:
            ret = self.data["retention"]
            self.retention = RetentionPolicy(
                daily=ret.get("daily", 7),
                weekly=ret.get("weekly", 4),
                monthly=ret.get("monthly", 12),
                max_storage_gb=ret.get("max_storage_gb", 0),
                warning_threshold_percent=ret.get("warning_threshold_percent", 80),
                cleanup_threshold_percent=ret.get("cleanup_threshold_percent", 90),
                cleanup_strategy=ret.get("cleanup_strategy", "oldest_first"),
            )
        
        # Parse incremental settings
        if "incremental" in self.data:
            inc = self.data["incremental"]
            self.incremental = IncrementalSettings(
                enabled=inc.get("enabled", True),
                use_link_dest=inc.get("use_link_dest", True),
                min_file_size=inc.get("min_file_size", 1048576),
            )
    
    def get_staging_dir(self) -> str:
        """Get local staging directory."""
        return self.data.get("backup", {}).get("local_staging", "/tmp/bbackup_staging")
    
    def get_backup_set(self, name: str) -> Optional[BackupSet]:
        """Get backup set by name."""
        return self.backup_sets.get(name)
    
    def get_enabled_remotes(self) -> List[RemoteStorage]:
        """Get list of enabled remote storage destinations."""
        return [r for r in self.remotes.values() if r.enabled]

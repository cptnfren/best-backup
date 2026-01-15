"""
Backup runner with status tracking for live TUI updates.
"""

import time
from pathlib import Path
from typing import List, Optional, Callable
from .config import Config, BackupScope
from .docker_backup import DockerBackup
from .remote import RemoteStorageManager
from .rotation import BackupRotation
from .tui import BackupStatus
from .logging import get_logger

logger = get_logger('backup_runner')


class BackupRunner:
    """Runs backup operations with status tracking."""
    
    def __init__(self, config: Config, status: BackupStatus):
        self.config = config
        self.status = status
        self.docker_backup = DockerBackup(config)
        self.remote_mgr = RemoteStorageManager(config)
        self.rotation = BackupRotation(config.retention)
    
    def run_backup(
        self,
        backup_dir: Path,
        containers: Optional[List[str]] = None,
        scope: Optional[BackupScope] = None,
        incremental: bool = False,
    ) -> dict:
        """Run backup with status updates."""
        if scope is None:
            scope = self.config.scope
        
        backup_dir = Path(backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        results = {
            "containers": {},
            "volumes": {},
            "networks": {},
            "errors": [],
        }
        
        self.status.start()
        
        # Calculate total items
        total_items = 0
        if scope.containers or scope.configs:
            containers_to_backup = containers or [c["name"] for c in self.docker_backup.get_all_containers()]
            total_items += len(containers_to_backup)
        if scope.volumes:
            if containers:
                container_volumes = self.docker_backup._get_container_volumes(containers)
            else:
                container_volumes = [v["name"] for v in self.docker_backup.get_all_volumes()]
            total_items += len(container_volumes)
        if scope.networks:
            networks = self.docker_backup.get_all_networks()
            total_items += len(networks)
        
        self.status.update(total=total_items, completed=0)
        
        completed = 0
        
        # Backup containers
        if (scope.containers or scope.configs) and not self.status.status == "cancelled":
            containers_to_backup = containers or [c["name"] for c in self.docker_backup.get_all_containers()]
            
            configs_dir = backup_dir / "configs"
            configs_dir.mkdir(parents=True, exist_ok=True)
            
            for container_name in containers_to_backup:
                if self.status.status == "cancelled":
                    break
                
                # Wait if paused
                while self.status.status == "paused" and not self.status.status == "cancelled":
                    time.sleep(0.5)
                
                if self.status.status == "cancelled":
                    break
                
                # Check if skip requested
                if self.status.skip_current:
                    logger.info(f"Skipping container: {container_name}")
                    self.status.skip_current = False
                    results["containers"][container_name] = "skipped"
                    self.status.containers_status[container_name] = "skipped"
                    completed += 1
                    self.status.update(completed=completed)
                    continue
                
                self.status.update(
                    action=f"Backing up container: {container_name}",
                    item=container_name,
                    completed=completed,
                )
                
                if scope.configs:
                    logger.info(f"Backing up container config: {container_name}")
                    success = self.docker_backup.backup_container_config(container_name, configs_dir)
                    results["containers"][container_name] = "success" if success else "failed"
                    self.status.containers_status[container_name] = "success" if success else "failed"
                    if not success:
                        error_msg = f"Failed to backup container config: {container_name}"
                        logger.error(error_msg)
                        results["errors"].append(error_msg)
                        self.status.add_error(error_msg)
                
                completed += 1
                self.status.update(completed=completed)
        
        # Backup volumes
        if scope.volumes and not self.status.status == "cancelled":
            volumes_dir = backup_dir / "volumes"
            volumes_dir.mkdir(parents=True, exist_ok=True)
            
            # Get volumes for selected containers
            if containers:
                container_volumes = self.docker_backup._get_container_volumes(containers)
            else:
                container_volumes = [v["name"] for v in self.docker_backup.get_all_volumes()]
            
            for volume_name in container_volumes:
                if self.status.status == "cancelled":
                    break
                
                # Wait if paused
                while self.status.status == "paused" and not self.status.status == "cancelled":
                    time.sleep(0.5)
                
                if self.status.status == "cancelled":
                    break
                
                # Check if skip requested
                if self.status.skip_current:
                    logger.info(f"Skipping volume: {volume_name}")
                    self.status.skip_current = False
                    results["volumes"][volume_name] = "skipped"
                    self.status.volumes_status[volume_name] = "skipped"
                    completed += 1
                    self.status.update(completed=completed)
                    continue
                
                self.status.update(
                    action=f"Backing up volume: {volume_name}",
                    item=volume_name,
                    completed=completed,
                )
                
                logger.info(f"Backing up volume: {volume_name} (incremental={incremental})")
                success = self.docker_backup.backup_volume(volume_name, backup_dir, incremental)
                results["volumes"][volume_name] = "success" if success else "failed"
                self.status.volumes_status[volume_name] = "success" if success else "failed"
                if not success:
                    error_msg = f"Failed to backup volume: {volume_name}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
                    self.status.add_error(error_msg)
                
                completed += 1
                self.status.update(completed=completed)
        
        # Backup networks
        if scope.networks and not self.status.status == "cancelled":
            networks = self.docker_backup.get_all_networks()
            for network in networks:
                if self.status.status == "cancelled":
                    break
                
                # Wait if paused
                while self.status.status == "paused" and not self.status.status == "cancelled":
                    time.sleep(0.5)
                
                if self.status.status == "cancelled":
                    break
                
                # Check if skip requested
                if self.status.skip_current:
                    logger.info(f"Skipping network: {network['name']}")
                    self.status.skip_current = False
                    results["networks"][network["name"]] = "skipped"
                    self.status.networks_status[network["name"]] = "skipped"
                    completed += 1
                    self.status.update(completed=completed)
                    continue
                
                self.status.update(
                    action=f"Backing up network: {network['name']}",
                    item=network["name"],
                    completed=completed,
                )
                
                logger.info(f"Backing up network: {network['name']}")
                success = self.docker_backup.backup_network(network["name"], backup_dir)
                results["networks"][network["name"]] = "success" if success else "failed"
                self.status.networks_status[network["name"]] = "success" if success else "failed"
                if not success:
                    error_msg = f"Failed to backup network: {network['name']}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
                    self.status.add_error(error_msg)
                
                completed += 1
                self.status.update(completed=completed)
        
        if self.status.status == "cancelled":
            self.status.status = "cancelled"
        else:
            self.status.status = "completed"
        
        return results
    
    def upload_to_remotes(
        self,
        backup_path: Path,
        backup_name: str,
        remotes: List,
    ):
        """Upload backup to remote destinations."""
        if not remotes:
            return
        
        logger.info(f"Starting upload to {len(remotes)} remote destination(s)")
        self.status.update(
            action=f"Uploading to {len(remotes)} remote destination(s)",
            item="",
        )
        
        for remote in remotes:
            if self.status.status == "cancelled":
                break
            
            logger.info(f"Uploading to remote: {remote.name} ({remote.type})")
            self.status.update(
                action=f"Uploading to {remote.name}...",
                item=remote.name,
            )
            
            self.status.remote_status[remote.name] = "uploading"
            
            # Create progress callback for TUI updates
            def progress_callback(line: str):
                """Parse rclone progress and update status."""
                if "Transferred:" in line or "Speed:" in line:
                    # Update status with progress info
                    self.status.update(item=f"{remote.name}: {line.strip()[:50]}")
            
            success = self.remote_mgr.upload_backup(remote, backup_path, backup_name, progress_callback)
            
            if success:
                logger.info(f"Successfully uploaded to {remote.name}")
                self.status.remote_status[remote.name] = "success"
                
                # Check storage quota and cleanup if needed
                try:
                    # remote.path is a string, not a Path
                    # For quota checking, we need the base remote path
                    quota_path = Path(remote.path).expanduser() if remote.type == "local" else Path("/tmp")
                    quota_status = self.rotation.check_storage_quota(remote, quota_path)
                    
                    if quota_status["cleanup_needed"]:
                        logger.warning(f"Storage quota exceeded for {remote.name}, starting cleanup")
                        self.status.add_warning(f"Storage quota exceeded for {remote.name}, cleaning up old backups")
                        
                        # Get list of backups
                        backups = self.remote_mgr.list_backups(remote)
                        if backups:
                            # Filter backups by retention policy
                            # filter_backups_by_retention expects a Path but only uses it for local remotes
                            rotation_path = Path(remote.path).expanduser() if remote.type == "local" else Path("/tmp")
                            to_keep, to_delete = self.rotation.filter_backups_by_retention(backups, rotation_path)
                            
                            if to_delete:
                                # For cleanup, use the actual remote path
                                cleanup_path = Path(remote.path).expanduser() if remote.type == "local" else Path("/tmp")
                                deleted_count = self.rotation.cleanup_old_backups(remote, cleanup_path, to_delete)
                                logger.info(f"Cleaned up {deleted_count} old backup(s) from {remote.name}")
                                self.status.add_warning(f"Cleaned up {deleted_count} old backup(s) from {remote.name}")
                    elif quota_status["warning"]:
                        logger.warning(f"Storage quota warning for {remote.name}: {quota_status['percent']:.1f}% used")
                        self.status.add_warning(f"Storage quota warning for {remote.name}: {quota_status['percent']:.1f}% used")
                except Exception as e:
                    logger.error(f"Error during rotation check for {remote.name}: {e}")
                    # Don't fail the upload if rotation check fails
            else:
                logger.error(f"Failed to upload to {remote.name}")
                self.status.remote_status[remote.name] = "failed"
                self.status.add_error(f"Failed to upload to {remote.name}")

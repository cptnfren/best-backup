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


class BackupRunner:
    """Runs backup operations with status tracking."""
    
    def __init__(self, config: Config, status: BackupStatus):
        self.config = config
        self.status = status
        self.docker_backup = DockerBackup(config)
        self.remote_mgr = RemoteStorageManager(config)
    
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
                
                self.status.update(
                    action=f"Backing up container: {container_name}",
                    item=container_name,
                    completed=completed,
                )
                
                if scope.configs:
                    success = self.docker_backup.backup_container_config(container_name, configs_dir)
                    results["containers"][container_name] = "success" if success else "failed"
                    self.status.containers_status[container_name] = "success" if success else "failed"
                    if not success:
                        error_msg = f"Failed to backup container config: {container_name}"
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
                
                self.status.update(
                    action=f"Backing up volume: {volume_name}",
                    item=volume_name,
                    completed=completed,
                )
                
                success = self.docker_backup.backup_volume(volume_name, backup_dir, incremental)
                results["volumes"][volume_name] = "success" if success else "failed"
                self.status.volumes_status[volume_name] = "success" if success else "failed"
                if not success:
                    error_msg = f"Failed to backup volume: {volume_name}"
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
                
                self.status.update(
                    action=f"Backing up network: {network['name']}",
                    item=network["name"],
                    completed=completed,
                )
                
                success = self.docker_backup.backup_network(network["name"], backup_dir)
                results["networks"][network["name"]] = "success" if success else "failed"
                self.status.networks_status[network["name"]] = "success" if success else "failed"
                if not success:
                    error_msg = f"Failed to backup network: {network['name']}"
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
        
        self.status.update(
            action=f"Uploading to {len(remotes)} remote destination(s)",
            item="",
        )
        
        for remote in remotes:
            if self.status.status == "cancelled":
                break
            
            self.status.update(
                action=f"Uploading to {remote.name}...",
                item=remote.name,
            )
            
            self.status.remote_status[remote.name] = "uploading"
            
            success = self.remote_mgr.upload_backup(remote, backup_path, backup_name)
            
            if success:
                self.status.remote_status[remote.name] = "success"
            else:
                self.status.remote_status[remote.name] = "failed"
                self.status.add_error(f"Failed to upload to {remote.name}")

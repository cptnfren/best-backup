"""
Docker backup functionality.
Handles backing up containers, volumes, networks, and metadata.
"""

import os
import json
import subprocess
import tarfile
from pathlib import Path
from typing import List, Dict, Optional, Set
from datetime import datetime
import docker
from docker.errors import DockerException, APIError

from .config import BackupScope, Config


class DockerBackup:
    """Docker backup manager."""
    
    def __init__(self, config: Config):
        self.config = config
        try:
            self.client = docker.from_env()
        except DockerException as e:
            raise RuntimeError(f"Failed to connect to Docker: {e}")
    
    def get_all_containers(self) -> List[Dict]:
        """Get list of all containers."""
        try:
            containers = self.client.containers.list(all=True)
            return [
                {
                    "id": c.id,
                    "name": c.name,
                    "status": c.status,
                    "image": c.image.tags[0] if c.image.tags else "unknown",
                }
                for c in containers
            ]
        except APIError as e:
            raise RuntimeError(f"Failed to list containers: {e}")
    
    def get_all_volumes(self) -> List[Dict]:
        """Get list of all volumes."""
        try:
            volumes = self.client.volumes.list()
            return [
                {
                    "name": v.name,
                    "driver": v.attrs.get("Driver", "local"),
                    "mountpoint": v.attrs.get("Mountpoint", ""),
                }
                for v in volumes
            ]
        except APIError as e:
            raise RuntimeError(f"Failed to list volumes: {e}")
    
    def get_all_networks(self) -> List[Dict]:
        """Get list of all networks."""
        try:
            networks = self.client.networks.list()
            return [
                {
                    "id": n.id,
                    "name": n.name,
                    "driver": n.attrs.get("Driver", ""),
                }
                for n in networks
                if not n.name.startswith("bridge") and n.name != "host" and n.name != "none"
            ]
        except APIError as e:
            raise RuntimeError(f"Failed to list networks: {e}")
    
    def backup_container_config(self, container_name: str, backup_dir: Path) -> bool:
        """Backup container configuration (inspect data)."""
        try:
            container = self.client.containers.get(container_name)
            inspect_data = container.attrs
            
            config_file = backup_dir / f"{container_name}_config.json"
            with open(config_file, 'w') as f:
                json.dump(inspect_data, f, indent=2)
            
            # Also save logs
            try:
                logs = container.logs(tail=1000).decode('utf-8', errors='replace')
                log_file = backup_dir / f"{container_name}_logs.txt"
                with open(log_file, 'w') as f:
                    f.write(logs)
            except Exception:
                pass  # Logs might not be available
            
            return True
        except APIError as e:
            return False
    
    def backup_volume(self, volume_name: str, backup_dir: Path, incremental: bool = False) -> bool:
        """Backup Docker volume using Docker container and rsync."""
        try:
            volume = self.client.volumes.get(volume_name)
            volume_backup_dir = backup_dir / "volumes" / volume_name
            volume_backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Use a temporary container to access the volume
            # This avoids permission issues with direct mountpoint access
            temp_container_name = f"bbackup_temp_{volume_name}_{os.getpid()}"
            
            try:
                # Create temporary container with volume mounted
                temp_container = self.client.containers.run(
                    "alpine:latest",
                    command="sleep 3600",  # Keep container running
                    name=temp_container_name,
                    volumes={volume_name: {"bind": "/volume_data", "mode": "ro"}},
                    detach=True,
                    remove=False,
                )
                
                # Wait a moment for container to start
                import time
                time.sleep(1)
                
                # Use rsync via docker exec to copy from container
                # First, check if rsync is available in alpine
                # If not, use tar for backup
                check_rsync = subprocess.run(
                    ["docker", "exec", temp_container_name, "which", "rsync"],
                    capture_output=True,
                    text=True,
                )
                
                if check_rsync.returncode == 0:
                    # Use rsync if available
                    rsync_cmd = [
                        "docker", "exec", temp_container_name,
                        "rsync", "-av", "--delete", "/volume_data/", "/tmp/backup/"
                    ]
                    
                    # Create backup directory in container
                    subprocess.run(
                        ["docker", "exec", temp_container_name, "mkdir", "-p", "/tmp/backup"],
                        check=False,
                    )
                    
                    result = subprocess.run(rsync_cmd, capture_output=True, text=True, check=False)
                    
                    if result.returncode == 0:
                        # Copy from container to host
                        subprocess.run(
                            ["docker", "cp", f"{temp_container_name}:/tmp/backup/.", str(volume_backup_dir)],
                            check=False,
                        )
                else:
                    # Fallback to tar if rsync not available
                    tar_cmd = [
                        "docker", "exec", temp_container_name,
                        "tar", "czf", "/tmp/volume_backup.tar.gz", "-C", "/volume_data", "."
                    ]
                    result = subprocess.run(tar_cmd, capture_output=True, text=True, check=False)
                    
                    if result.returncode == 0:
                        # Copy tar from container and extract
                        temp_tar = backup_dir / "volumes" / f"{volume_name}.tar.gz"
                        subprocess.run(
                            ["docker", "cp", f"{temp_container_name}:/tmp/volume_backup.tar.gz", str(temp_tar)],
                            check=False,
                        )
                        # Extract tar
                        import tarfile
                        with tarfile.open(temp_tar, "r:gz") as tar:
                            tar.extractall(volume_backup_dir)
                        temp_tar.unlink()
                
                # Cleanup
                temp_container.stop()
                temp_container.remove()
                
                return True
                
            except Exception as e:
                # Cleanup on error
                try:
                    temp_container = self.client.containers.get(temp_container_name)
                    temp_container.stop()
                    temp_container.remove()
                except:
                    pass
                return False
                
        except APIError:
            return False
    
    def _find_previous_volume_backup(self, volume_name: str, backups_root: Path) -> Optional[Path]:
        """Find previous backup of volume for incremental backup."""
        if not backups_root.exists():
            return None
        
        # Look for most recent backup
        backup_dirs = sorted(
            [d for d in backups_root.iterdir() if d.is_dir()],
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )
        
        for backup_dir in backup_dirs:
            prev_volume_dir = backup_dir / "volumes" / volume_name
            if prev_volume_dir.exists():
                return prev_volume_dir
        
        return None
    
    def backup_network(self, network_name: str, backup_dir: Path) -> bool:
        """Backup network configuration."""
        try:
            network = self.client.networks.get(network_name)
            network_data = network.attrs
            
            network_file = backup_dir / "networks" / f"{network_name}.json"
            network_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(network_file, 'w') as f:
                json.dump(network_data, f, indent=2)
            
            return True
        except APIError:
            return False
    
    def create_metadata_archive(self, backup_dir: Path, output_file: Path) -> bool:
        """Create compressed tar archive of metadata (configs, networks)."""
        try:
            compression = self.config.data.get("backup", {}).get("compression", {})
            format = compression.get("format", "gzip")
            
            mode_map = {
                "gzip": "w:gz",
                "bzip2": "w:bz2",
                "xz": "w:xz",
            }
            mode = mode_map.get(format, "w:gz")
            
            with tarfile.open(output_file, mode) as tar:
                # Add configs
                configs_dir = backup_dir / "configs"
                if configs_dir.exists():
                    tar.add(configs_dir, arcname="configs")
                
                # Add networks
                networks_dir = backup_dir / "networks"
                if networks_dir.exists():
                    tar.add(networks_dir, arcname="networks")
                
                # Add metadata file
                metadata = {
                    "timestamp": datetime.now().isoformat(),
                    "backup_version": "1.0",
                    "docker_version": self.client.version().get("Version", "unknown"),
                }
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
                    json.dump(metadata, f, indent=2)
                    temp_meta = f.name
                
                tar.add(temp_meta, arcname="backup_metadata.json")
                os.unlink(temp_meta)
            
            return True
        except Exception as e:
            return False
    
    def create_backup(
        self,
        backup_dir: Path,
        containers: Optional[List[str]] = None,
        scope: Optional[BackupScope] = None,
        incremental: bool = False,
    ) -> Dict[str, any]:
        """Create complete backup."""
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
        
        # Backup containers
        if scope.containers or scope.configs:
            containers_to_backup = containers or [c["name"] for c in self.get_all_containers()]
            
            configs_dir = backup_dir / "configs"
            configs_dir.mkdir(parents=True, exist_ok=True)
            
            for container_name in containers_to_backup:
                if scope.configs:
                    success = self.backup_container_config(container_name, configs_dir)
                    results["containers"][container_name] = "success" if success else "failed"
                    if not success:
                        results["errors"].append(f"Failed to backup container config: {container_name}")
        
        # Backup volumes
        if scope.volumes:
            volumes_dir = backup_dir / "volumes"
            volumes_dir.mkdir(parents=True, exist_ok=True)
            
            # Get volumes for selected containers
            if containers:
                container_volumes = self._get_container_volumes(containers)
            else:
                container_volumes = [v["name"] for v in self.get_all_volumes()]
            
            for volume_name in container_volumes:
                success = self.backup_volume(volume_name, backup_dir, incremental)
                results["volumes"][volume_name] = "success" if success else "failed"
                if not success:
                    results["errors"].append(f"Failed to backup volume: {volume_name}")
        
        # Backup networks
        if scope.networks:
            networks = self.get_all_networks()
            for network in networks:
                success = self.backup_network(network["name"], backup_dir)
                results["networks"][network["name"]] = "success" if success else "failed"
                if not success:
                    results["errors"].append(f"Failed to backup network: {network['name']}")
        
        return results
    
    def _get_container_volumes(self, container_names: List[str]) -> Set[str]:
        """Get volume names used by containers."""
        volumes = set()
        for container_name in container_names:
            try:
                container = self.client.containers.get(container_name)
                mounts = container.attrs.get("Mounts", [])
                for mount in mounts:
                    if mount.get("Type") == "volume":
                        volumes.add(mount.get("Name"))
            except APIError:
                continue
        return volumes

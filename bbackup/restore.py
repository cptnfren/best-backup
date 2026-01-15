"""
Docker restore functionality.
Handles restoring containers, volumes, networks, and metadata from backups.
"""

import os
import json
import subprocess
import tarfile
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import docker
from docker.errors import DockerException, APIError

from .config import Config


class DockerRestore:
    """Docker restore manager."""
    
    def __init__(self, config: Config):
        self.config = config
        try:
            self.client = docker.from_env()
        except DockerException as e:
            raise RuntimeError(f"Failed to connect to Docker: {e}")
    
    def list_backups(self, backup_dir: Path) -> List[Dict]:
        """List available backups in backup directory."""
        backups = []
        if not backup_dir.exists():
            return backups
        
        for backup_path in sorted(backup_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if backup_path.is_dir() and backup_path.name.startswith("backup_"):
                # Try to read metadata
                metadata_file = backup_path / "backup_metadata.json"
                timestamp = None
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                            timestamp = metadata.get("timestamp")
                    except:
                        pass
                
                # Parse timestamp from name if metadata not available
                if not timestamp:
                    try:
                        # backup_YYYYMMDD_HHMMSS
                        name_part = backup_path.name.replace("backup_", "")
                        timestamp = datetime.strptime(name_part, "%Y%m%d_%H%M%S").isoformat()
                    except:
                        timestamp = backup_path.name
                
                backups.append({
                    "name": backup_path.name,
                    "path": backup_path,
                    "timestamp": timestamp,
                })
        
        return backups
    
    def restore_container_config(self, container_name: str, backup_path: Path, new_name: Optional[str] = None) -> bool:
        """Restore container from backup configuration."""
        try:
            config_file = backup_path / "configs" / f"{container_name}_config.json"
            if not config_file.exists():
                return False
            
            with open(config_file, 'r') as f:
                container_config = json.load(f)
            
            # Extract container configuration
            image = container_config.get("Config", {}).get("Image", "")
            if not image:
                return False
            
            # Get environment variables
            env_vars = container_config.get("Config", {}).get("Env", [])
            env_dict = {}
            for env in env_vars:
                if "=" in env:
                    key, value = env.split("=", 1)
                    env_dict[key] = value
            
            # Get port mappings
            port_bindings = {}
            if "NetworkSettings" in container_config and "Ports" in container_config["NetworkSettings"]:
                ports = container_config["NetworkSettings"]["Ports"]
                for container_port, host_ports in ports.items():
                    if host_ports:
                        port_bindings[container_port] = host_ports[0]["HostPort"]
            
            # Get volume mounts
            mounts = []
            if "Mounts" in container_config:
                for mount in container_config["Mounts"]:
                    if mount.get("Type") == "volume":
                        mounts.append(f"{mount['Name']}:{mount['Destination']}")
                    elif mount.get("Type") == "bind":
                        mounts.append(f"{mount['Source']}:{mount['Destination']}")
            
            # Get restart policy
            restart_policy = container_config.get("HostConfig", {}).get("RestartPolicy", {}).get("Name", "no")
            
            # Get network
            networks = []
            if "NetworkSettings" in container_config and "Networks" in container_config["NetworkSettings"]:
                networks = list(container_config["NetworkSettings"]["Networks"].keys())
            
            # Stop and remove existing container if it exists
            target_name = new_name or container_name
            try:
                existing = self.client.containers.get(target_name)
                existing.stop()
                existing.remove()
            except APIError:
                pass  # Container doesn't exist
            
            # Create new container
            container = self.client.containers.create(
                image=image,
                name=target_name,
                environment=env_dict,
                ports=port_bindings,
                volumes=mounts,
                restart_policy={"Name": restart_policy},
                detach=True,
            )
            
            # Connect to networks
            for network_name in networks:
                try:
                    network = self.client.networks.get(network_name)
                    network.connect(container)
                except APIError:
                    pass  # Network might not exist
            
            return True
        except Exception as e:
            return False
    
    def restore_volume(self, volume_name: str, backup_path: Path, new_name: Optional[str] = None) -> bool:
        """Restore Docker volume from backup."""
        try:
            volume_backup_dir = backup_path / "volumes" / volume_name
            if not volume_backup_dir.exists():
                return False
            
            target_volume_name = new_name or volume_name
            
            # Remove existing volume if it exists
            try:
                existing_volume = self.client.volumes.get(target_volume_name)
                existing_volume.remove()
            except APIError:
                pass  # Volume doesn't exist
            
            # Create new volume
            volume = self.client.volumes.create(name=target_volume_name)
            
            # Use temporary container to restore volume data
            temp_container_name = f"bbackup_restore_{target_volume_name}_{os.getpid()}"
            
            try:
                # Create temporary container with volume mounted
                temp_container = self.client.containers.run(
                    "alpine:latest",
                    command="sleep 3600",
                    name=temp_container_name,
                    volumes={target_volume_name: {"bind": "/volume_data", "mode": "rw"}},
                    detach=True,
                    remove=False,
                )
                
                import time
                time.sleep(1)
                
                # Copy backup data to container
                subprocess.run(
                    ["docker", "cp", str(volume_backup_dir) + "/.", f"{temp_container_name}:/volume_data/"],
                    check=False,
                )
                
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
    
    def restore_network(self, network_name: str, backup_path: Path, new_name: Optional[str] = None) -> bool:
        """Restore network configuration."""
        try:
            network_file = backup_path / "networks" / f"{network_name}.json"
            if not network_file.exists():
                return False
            
            with open(network_file, 'r') as f:
                network_config = json.load(f)
            
            target_name = new_name or network_name
            
            # Remove existing network if it exists (except default networks)
            if target_name not in ["bridge", "host", "none"]:
                try:
                    existing = self.client.networks.get(target_name)
                    existing.remove()
                except APIError:
                    pass  # Network doesn't exist
                
                # Create network
                driver = network_config.get("Driver", "bridge")
                options = network_config.get("Options", {})
                ipam = network_config.get("IPAM", {})
                
                self.client.networks.create(
                    name=target_name,
                    driver=driver,
                    options=options,
                    ipam=ipam,
                )
            
            return True
        except APIError:
            return False
    
    def restore_backup(
        self,
        backup_path: Path,
        containers: Optional[List[str]] = None,
        volumes: Optional[List[str]] = None,
        networks: Optional[List[str]] = None,
        rename_map: Optional[Dict[str, str]] = None,
    ) -> Dict[str, any]:
        """Restore complete backup."""
        rename_map = rename_map or {}
        
        results = {
            "containers": {},
            "volumes": {},
            "networks": {},
            "errors": [],
        }
        
        # Restore containers
        if containers is not None:
            configs_dir = backup_path / "configs"
            if configs_dir.exists():
                for container_name in containers:
                    new_name = rename_map.get(container_name)
                    success = self.restore_container_config(container_name, backup_path, new_name)
                    results["containers"][container_name] = "success" if success else "failed"
                    if not success:
                        results["errors"].append(f"Failed to restore container: {container_name}")
        
        # Restore volumes
        if volumes is not None:
            volumes_dir = backup_path / "volumes"
            if volumes_dir.exists():
                for volume_name in volumes:
                    new_name = rename_map.get(volume_name)
                    success = self.restore_volume(volume_name, backup_path, new_name)
                    results["volumes"][volume_name] = "success" if success else "failed"
                    if not success:
                        results["errors"].append(f"Failed to restore volume: {volume_name}")
        
        # Restore networks
        if networks is not None:
            networks_dir = backup_path / "networks"
            if networks_dir.exists():
                for network_name in networks:
                    new_name = rename_map.get(network_name)
                    success = self.restore_network(network_name, backup_path, new_name)
                    results["networks"][network_name] = "success" if success else "failed"
                    if not success:
                        results["errors"].append(f"Failed to restore network: {network_name}")
        
        return results

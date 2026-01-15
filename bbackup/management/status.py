"""
Backup status and history management.
"""

import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

from rich.console import Console
from rich.table import Table
from rich import box

from ..config import Config

console = Console()


def list_local_backups(config: Optional[Config] = None) -> List[Dict]:
    """
    List local backups from staging directory.
    
    Args:
        config: Config object (creates new if None)
    
    Returns:
        List of backup info dicts
    """
    if config is None:
        config = Config()
    
    staging_dir = Path(config.get_staging_dir()).expanduser()
    backups = []
    
    if not staging_dir.exists():
        return backups
    
    for backup_dir in staging_dir.iterdir():
        if backup_dir.is_dir() and backup_dir.name.startswith("backup_"):
            try:
                # Parse timestamp from directory name
                timestamp_str = backup_dir.name.replace("backup_", "")
                timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                
                # Get size
                size = sum(f.stat().st_size for f in backup_dir.rglob('*') if f.is_file())
                
                # Check if encrypted
                encrypted = (backup_dir / "encryption_metadata.json").exists() or backup_dir.name.endswith(".enc")
                
                backups.append({
                    "name": backup_dir.name,
                    "path": str(backup_dir),
                    "timestamp": timestamp,
                    "size": size,
                    "encrypted": encrypted,
                })
            except Exception:
                pass
    
    # Sort by timestamp (newest first)
    backups.sort(key=lambda x: x["timestamp"], reverse=True)
    return backups


def get_backup_statistics(config: Optional[Config] = None) -> Dict:
    """
    Get backup statistics.
    
    Args:
        config: Config object (creates new if None)
    
    Returns:
        Dict with statistics
    """
    backups = list_local_backups(config)
    
    total_size = sum(b["size"] for b in backups)
    encrypted_count = sum(1 for b in backups if b["encrypted"])
    
    return {
        "total_backups": len(backups),
        "total_size": total_size,
        "encrypted_backups": encrypted_count,
        "latest_backup": backups[0]["timestamp"] if backups else None,
    }


def display_backup_status(config: Optional[Config] = None):
    """Display backup status in a formatted table."""
    backups = list_local_backups(config)
    stats = get_backup_statistics(config)
    
    console.print(f"\n[bold cyan]Backup Status[/bold cyan]")
    console.print(f"Total backups: {stats['total_backups']}")
    console.print(f"Total size: {stats['total_size'] / (1024*1024):.2f} MB")
    console.print(f"Encrypted: {stats['encrypted_backups']}")
    
    if backups:
        console.print(f"\n[bold]Recent Backups:[/bold]")
        table = Table(show_header=True, header_style="bold cyan", box=box.SIMPLE)
        table.add_column("Name")
        table.add_column("Date")
        table.add_column("Size")
        table.add_column("Encrypted")
        
        for backup in backups[:10]:  # Show last 10
            size_mb = backup["size"] / (1024 * 1024)
            encrypted = "[green]✓[/green]" if backup["encrypted"] else "[dim]○[/dim]"
            table.add_row(
                backup["name"],
                backup["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
                f"{size_mb:.2f} MB",
                encrypted
            )
        
        console.print(table)
    else:
        console.print("[dim]No backups found[/dim]")

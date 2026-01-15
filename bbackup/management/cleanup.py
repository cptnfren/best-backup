"""
Cleanup operations for old files and backups.
"""

import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from rich.console import Console
from rich.prompt import Confirm

from ..config import Config

console = Console()


def cleanup_staging_files(config: Optional[Config] = None, days: int = 7) -> int:
    """
    Cleanup old staging files.
    
    Args:
        config: Config object (creates new if None)
        days: Keep files newer than this many days
    
    Returns:
        Number of files/directories removed
    """
    if config is None:
        config = Config()
    
    staging_dir = Path(config.get_staging_dir()).expanduser()
    if not staging_dir.exists():
        return 0
    
    cutoff = datetime.now() - timedelta(days=days)
    removed = 0
    
    for item in staging_dir.iterdir():
        try:
            mtime = datetime.fromtimestamp(item.stat().st_mtime)
            if mtime < cutoff:
                if item.is_dir():
                    import shutil
                    shutil.rmtree(item)
                else:
                    item.unlink()
                removed += 1
        except Exception:
            pass
    
    return removed


def cleanup_log_files(config: Optional[Config] = None, days: int = 30) -> int:
    """
    Cleanup old log files.
    
    Args:
        config: Config object (creates new if None)
        days: Keep logs newer than this many days
    
    Returns:
        Number of log files removed
    """
    if config is None:
        config = Config()
    
    log_file_str = config.data.get('logging', {}).get('file', '~/.local/share/bbackup/bbackup.log')
    log_path = Path(log_file_str).expanduser()
    log_dir = log_path.parent
    
    if not log_dir.exists():
        return 0
    
    cutoff = datetime.now() - timedelta(days=days)
    removed = 0
    
    # Remove old rotated log files
    for log_file in log_dir.glob("*.log.*"):
        try:
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if mtime < cutoff:
                log_file.unlink()
                removed += 1
        except Exception:
            pass
    
    return removed


def cleanup_old_backups(config: Optional[Config] = None) -> Dict:
    """
    Cleanup old backups using rotation policy.
    
    Args:
        config: Config object (creates new if None)
    
    Returns:
        Dict with cleanup results
    """
    if config is None:
        config = Config()
    
    from ..rotation import BackupRotation
    rotation = BackupRotation(config.retention)
    
    # Get all backups
    from .status import list_local_backups
    backups = list_local_backups(config)
    
    if not backups:
        return {"removed": 0, "freed_space": 0}
    
    # Filter by retention policy
    # BackupRotation.filter_backups_by_retention expects List[Dict] with backup info
    # and remote_path as Path
    staging_dir = Path(config.get_staging_dir()).expanduser()
    
    # Convert backups to format expected by BackupRotation
    # The rotation.py code expects backup names as strings in a list
    # but the type hint says List[Dict] - this is inconsistent
    # Looking at the code: _parse_backup_date expects a string and does .split("_")
    # So we pass backup names as strings
    backup_names = [Path(b["path"]).name for b in backups]
    
    # Filter by retention policy
    # The method signature says List[Dict] but implementation treats items as strings
    # Pass as list of strings (backup names) - the type hint is incorrect
    try:
        to_keep_names, to_delete_names = rotation.filter_backups_by_retention(
            backup_names,  # Pass as list of strings (backup names)
            staging_dir
        )
        to_remove = [staging_dir / name for name in to_delete_names]
    except (AttributeError, TypeError) as e:
        # Fallback: if API is broken, use simple date-based filtering
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() - timedelta(days=config.retention.daily)
        to_remove = []
        for b in backups:
            if b["timestamp"] < cutoff_date:
                to_remove.append(Path(b["path"]))
    
    # Calculate space to free
    freed_space = sum(
        sum(f.stat().st_size for f in backup.rglob('*') if f.is_file())
        for backup in to_remove
    )
    
    # Remove backups
    removed = 0
    for backup in to_remove:
        try:
            import shutil
            shutil.rmtree(backup)
            removed += 1
        except Exception:
            pass
    
    return {
        "removed": removed,
        "freed_space": freed_space,
        "kept": len(backups) - removed,
    }


def cleanup_temporary_files() -> int:
    """
    Cleanup temporary files.
    
    Returns:
        Number of files removed
    """
    temp_dirs = [
        Path("/tmp/bbackup_*"),
        Path.home() / ".cache" / "bbackup",
    ]
    
    removed = 0
    for temp_pattern in temp_dirs:
        if "*" in str(temp_pattern):
            # Handle glob patterns
            import glob
            for temp_path in glob.glob(str(temp_pattern)):
                try:
                    path = Path(temp_path)
                    if path.is_dir():
                        import shutil
                        shutil.rmtree(path)
                    else:
                        path.unlink()
                    removed += 1
                except Exception:
                    pass
        else:
            temp_path = Path(temp_pattern)
            if temp_path.exists():
                try:
                    if temp_path.is_dir():
                        import shutil
                        shutil.rmtree(temp_path)
                    else:
                        temp_path.unlink()
                    removed += 1
                except Exception:
                    pass
    
    return removed


def run_cleanup(
    config: Optional[Config] = None,
    staging_days: int = 7,
    log_days: int = 30,
    cleanup_backups: bool = True,
    cleanup_temp: bool = True,
    confirm: bool = True
) -> Dict:
    """
    Run comprehensive cleanup.
    
    Args:
        config: Config object (creates new if None)
        staging_days: Keep staging files newer than this many days
        log_days: Keep log files newer than this many days
        cleanup_backups: Whether to cleanup old backups
        cleanup_temp: Whether to cleanup temporary files
        confirm: Whether to ask for confirmation
    
    Returns:
        Dict with cleanup results
    """
    if config is None:
        config = Config()
    
    results = {
        "staging_removed": 0,
        "logs_removed": 0,
        "backups_removed": 0,
        "backups_freed_space": 0,
        "temp_removed": 0,
    }
    
    if confirm:
        console.print("[yellow]This will remove old files. Continue?[/yellow]")
        if not Confirm.ask("Proceed with cleanup?", default=False):
            console.print("[dim]Cleanup cancelled[/dim]")
            return results
    
    # Cleanup staging
    console.print("[cyan]Cleaning up staging files...[/cyan]")
    results["staging_removed"] = cleanup_staging_files(config, staging_days)
    console.print(f"[green]✓ Removed {results['staging_removed']} staging items[/green]")
    
    # Cleanup logs
    console.print("[cyan]Cleaning up log files...[/cyan]")
    results["logs_removed"] = cleanup_log_files(config, log_days)
    console.print(f"[green]✓ Removed {results['logs_removed']} log files[/green]")
    
    # Cleanup backups
    if cleanup_backups:
        console.print("[cyan]Cleaning up old backups...[/cyan]")
        backup_results = cleanup_old_backups(config)
        results["backups_removed"] = backup_results["removed"]
        results["backups_freed_space"] = backup_results["freed_space"]
        console.print(f"[green]✓ Removed {results['backups_removed']} backups[/green]")
        console.print(f"[green]✓ Freed {results['backups_freed_space'] / (1024*1024):.2f} MB[/green]")
    
    # Cleanup temp
    if cleanup_temp:
        console.print("[cyan]Cleaning up temporary files...[/cyan]")
        results["temp_removed"] = cleanup_temporary_files()
        console.print(f"[green]✓ Removed {results['temp_removed']} temporary items[/green]")
    
    return results

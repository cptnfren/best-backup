"""
Diagnostics and system information reporting.
"""

import os
import platform
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

import docker

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..config import Config
from ..logging import get_logger

console = Console()
logger = get_logger('management.diagnostics')


def get_system_info() -> Dict:
    """Get system information."""
    return {
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": sys.version,
        "python_executable": sys.executable,
    }


def get_docker_info() -> Dict:
    """Get Docker information."""
    try:
        client = docker.from_env()
        version = client.version()
        info = client.info()
        
        return {
            "accessible": True,
            "version": version.get("Version", "unknown"),
            "api_version": version.get("ApiVersion", "unknown"),
            "containers": info.get("Containers", 0),
            "images": info.get("Images", 0),
            "volumes": len(client.volumes.list()),
        }
    except Exception as e:
        return {
            "accessible": False,
            "error": str(e),
        }


def get_config_summary(config: Optional[Config] = None) -> Dict:
    """Get configuration summary."""
    if config is None:
        config = Config()
    
    return {
        "config_path": config.config_path or "default",
        "staging_dir": config.get_staging_dir(),
        "backup_sets": len(config.backup_sets),
        "remotes": len([r for r in config.remotes.values() if r.enabled]),
        "encryption_enabled": config.encryption.enabled if hasattr(config, 'encryption') else False,
    }


def get_recent_errors(log_file: Path, lines: int = 50) -> List[str]:
    """Get recent errors from log file."""
    errors = []
    
    if not log_file.exists():
        return errors
    
    try:
        with open(log_file, 'r') as f:
            all_lines = f.readlines()
            # Get last N lines
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            
            for line in recent_lines:
                if "ERROR" in line or "CRITICAL" in line:
                    errors.append(line.strip())
    except Exception:
        pass
    
    return errors


def run_diagnostics(config: Optional[Config] = None) -> Dict:
    """
    Run comprehensive diagnostics.
    
    Args:
        config: Config object (creates new if None)
    
    Returns:
        Dict with diagnostic information
    """
    if config is None:
        config = Config()
    
    diagnostics = {
        "timestamp": datetime.now().isoformat(),
        "system": get_system_info(),
        "docker": get_docker_info(),
        "config": get_config_summary(config),
    }
    
    # Get recent errors
    log_file_str = config.data.get('logging', {}).get('file', '~/.local/share/bbackup/bbackup.log')
    log_file = Path(log_file_str).expanduser()
    diagnostics["recent_errors"] = get_recent_errors(log_file)
    
    return diagnostics


def display_diagnostics_report(diagnostics: Dict):
    """Display diagnostics in formatted output."""
    console.print(Panel.fit(
        "[bold cyan]bbackup Diagnostics Report[/bold cyan]",
        title="Diagnostics"
    ))
    
    # System Information
    console.print("\n[bold]System Information:[/bold]")
    table = Table(show_header=False, box=None)
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="white")
    
    sys_info = diagnostics["system"]
    table.add_row("Platform", sys_info["platform"])
    table.add_row("System", sys_info["system"])
    table.add_row("Release", sys_info["release"])
    table.add_row("Python Version", sys_info["python_version"].split('\n')[0])
    table.add_row("Python Executable", sys_info["python_executable"])
    
    console.print(table)
    
    # Docker Information
    console.print("\n[bold]Docker Information:[/bold]")
    docker_info = diagnostics["docker"]
    if docker_info.get("accessible"):
        docker_table = Table(show_header=False, box=None)
        docker_table.add_column("Key", style="cyan")
        docker_table.add_column("Value", style="white")
        docker_table.add_row("Version", docker_info.get("version", "unknown"))
        docker_table.add_row("API Version", docker_info.get("api_version", "unknown"))
        docker_table.add_row("Containers", str(docker_info.get("containers", 0)))
        docker_table.add_row("Images", str(docker_info.get("images", 0)))
        docker_table.add_row("Volumes", str(docker_info.get("volumes", 0)))
        console.print(docker_table)
    else:
        console.print(f"[red]Docker not accessible: {docker_info.get('error', 'unknown error')}[/red]")
    
    # Configuration Summary
    console.print("\n[bold]Configuration Summary:[/bold]")
    config_table = Table(show_header=False, box=None)
    config_table.add_column("Key", style="cyan")
    config_table.add_column("Value", style="white")
    
    config_info = diagnostics["config"]
    config_table.add_row("Config Path", config_info.get("config_path", "unknown"))
    config_table.add_row("Staging Directory", config_info.get("staging_dir", "unknown"))
    config_table.add_row("Backup Sets", str(config_info.get("backup_sets", 0)))
    config_table.add_row("Enabled Remotes", str(config_info.get("remotes", 0)))
    config_table.add_row("Encryption Enabled", "Yes" if config_info.get("encryption_enabled") else "No")
    
    console.print(config_table)
    
    # Recent Errors
    errors = diagnostics.get("recent_errors", [])
    if errors:
        console.print(f"\n[bold yellow]Recent Errors ({len(errors)}):[/bold yellow]")
        for error in errors[-10:]:  # Show last 10
            console.print(f"[red]{error}[/red]")
    else:
        console.print("\n[green]✓ No recent errors found[/green]")


def generate_diagnostics_report(diagnostics: Dict, output_file: Optional[Path] = None) -> str:
    """
    Generate text diagnostics report.
    
    Args:
        diagnostics: Diagnostics data
        output_file: Optional file to save report to
    
    Returns:
        Report as string
    """
    report = []
    report.append("bbackup Diagnostics Report")
    report.append("=" * 50)
    report.append(f"Generated: {diagnostics['timestamp']}")
    report.append("")
    
    # System
    report.append("System Information:")
    report.append("-" * 30)
    sys_info = diagnostics["system"]
    report.append(f"Platform: {sys_info['platform']}")
    report.append(f"System: {sys_info['system']}")
    report.append(f"Release: {sys_info['release']}")
    report.append(f"Python: {sys_info['python_version'].split(chr(10))[0]}")
    report.append("")
    
    # Docker
    report.append("Docker Information:")
    report.append("-" * 30)
    docker_info = diagnostics["docker"]
    if docker_info.get("accessible"):
        report.append(f"Version: {docker_info.get('version', 'unknown')}")
        report.append(f"Containers: {docker_info.get('containers', 0)}")
        report.append(f"Images: {docker_info.get('images', 0)}")
    else:
        report.append(f"Not accessible: {docker_info.get('error', 'unknown')}")
    report.append("")
    
    # Config
    report.append("Configuration:")
    report.append("-" * 30)
    config_info = diagnostics["config"]
    report.append(f"Config Path: {config_info.get('config_path', 'unknown')}")
    report.append(f"Staging: {config_info.get('staging_dir', 'unknown')}")
    report.append("")
    
    # Errors
    errors = diagnostics.get("recent_errors", [])
    if errors:
        report.append(f"Recent Errors ({len(errors)}):")
        report.append("-" * 30)
        for error in errors:
            report.append(error)
    
    report_text = "\n".join(report)
    
    if output_file:
        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w') as f:
                f.write(report_text)
        except Exception:
            pass
    
    return report_text

"""
Dependency checking and installation.
"""

import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm

console = Console()


def check_system_dependencies() -> Dict[str, Tuple[bool, str]]:
    """
    Check system dependencies.
    
    Returns:
        Dict mapping tool names to (available, message) tuples
    """
    tools = {
        "docker": "Docker container runtime",
        "rsync": "rsync for efficient file copying",
        "tar": "tar for archive operations",
        "rclone": "rclone for Google Drive support (optional)",
    }
    
    results = {}
    for tool, description in tools.items():
        try:
            result = subprocess.run(
                ["which", tool],
                capture_output=True,
                text=True,
                timeout=2
            )
            available = result.returncode == 0
            if available:
                # Try to get version
                try:
                    version_result = subprocess.run(
                        [tool, "--version"],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    version = version_result.stdout.split('\n')[0] if version_result.returncode == 0 else ""
                    message = f"{description} - {version}" if version else f"{description} - installed"
                except Exception:
                    message = f"{description} - installed"
            else:
                message = f"{description} - not found"
            results[tool] = (available, message)
        except Exception as e:
            results[tool] = (False, f"{description} - error: {e}")
    
    return results


def check_python_dependencies() -> Tuple[bool, List[str], List[str]]:
    """
    Check Python package dependencies.
    
    Returns:
        Tuple of (all_installed, installed_packages, missing_packages)
    """
    required = {
        "rich": "rich",
        "pyyaml": "yaml",
        "docker": "docker",
        "click": "click",
        "paramiko": "paramiko",
        "cryptography": "cryptography",
        "requests": "requests",
    }
    
    installed = []
    missing = []
    
    for package_name, import_name in required.items():
        try:
            __import__(import_name)
            installed.append(package_name)
        except ImportError:
            missing.append(package_name)
    
    return len(missing) == 0, installed, missing


def check_requirements_file() -> List[str]:
    """
    Read requirements from requirements.txt.
    
    Returns:
        List of package names from requirements.txt
    """
    req_file = Path(__file__).parent.parent.parent / "requirements.txt"
    packages = []
    
    if req_file.exists():
        with open(req_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Extract package name (before ==, >=, etc.)
                    package = line.split('>=')[0].split('==')[0].split('>')[0].split('<')[0].strip()
                    if package:
                        packages.append(package)
    
    return packages


def install_python_packages(packages: List[str]) -> bool:
    """
    Install Python packages.
    
    Args:
        packages: List of package names to install
    
    Returns:
        True if successful
    """
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install"] + packages,
            check=True
        )
        return True
    except subprocess.CalledProcessError:
        return False


def check_and_install_dependencies(install_missing: bool = False) -> Dict:
    """
    Check all dependencies and optionally install missing ones.
    
    Args:
        install_missing: If True, prompt to install missing packages
    
    Returns:
        Dict with dependency check results
    """
    # Check system dependencies
    system_deps = check_system_dependencies()
    
    # Check Python dependencies
    all_installed, installed_pkgs, missing_pkgs = check_python_dependencies()
    
    # Check requirements.txt
    required_pkgs = check_requirements_file()
    
    results = {
        "system": system_deps,
        "python_installed": installed_pkgs,
        "python_missing": missing_pkgs,
        "python_all_installed": all_installed,
        "required_packages": required_pkgs,
    }
    
    # Install missing packages if requested
    if install_missing and missing_pkgs:
        console.print(f"\n[yellow]Missing Python packages: {', '.join(missing_pkgs)}[/yellow]")
        if Confirm.ask("Install missing packages?", default=True):
            if install_python_packages(missing_pkgs):
                console.print("[green]✓ Packages installed successfully[/green]")
                # Re-check
                all_installed, installed_pkgs, missing_pkgs = check_python_dependencies()
                results["python_installed"] = installed_pkgs
                results["python_missing"] = missing_pkgs
                results["python_all_installed"] = all_installed
            else:
                console.print("[red]✗ Failed to install packages[/red]")
    
    return results


def display_dependency_report(results: Dict):
    """Display dependency check results."""
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Dependency")
    table.add_column("Status")
    table.add_column("Details")
    
    # System dependencies
    for tool, (available, message) in results["system"].items():
        status = "[green]✓[/green]" if available else "[red]✗[/red]"
        table.add_row(f"System: {tool}", status, message)
    
    # Python dependencies
    if results["python_all_installed"]:
        table.add_row("Python Packages", "[green]✓[/green]", f"All installed ({len(results['python_installed'])})")
    else:
        table.add_row(
            "Python Packages",
            "[red]✗[/red]",
            f"Missing: {', '.join(results['python_missing'])}"
        )
    
    console.print(table)

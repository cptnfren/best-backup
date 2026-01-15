"""
First-run detection and marker file management.
"""

import os
from pathlib import Path


def get_data_dir() -> Path:
    """Get bbackup data directory."""
    return Path.home() / ".local" / "share" / "bbackup"


def get_config_file() -> Path:
    """Get config file path."""
    return Path.home() / ".config" / "bbackup" / "config.yaml"


def is_first_run() -> bool:
    """
    Check if this is the first run.
    
    Returns:
        True if first run, False otherwise
    """
    data_dir = get_data_dir()
    marker_file = data_dir / ".first_run_complete"
    config_file = get_config_file()
    
    # Check if marker exists
    if marker_file.exists():
        return False
    
    # Check if config exists
    if config_file.exists():
        return False
    
    # Check if config directory is empty
    config_dir = config_file.parent
    if config_dir.exists() and any(config_dir.iterdir()):
        return False
    
    return True


def mark_first_run_complete() -> bool:
    """
    Mark first run as complete.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        data_dir = get_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        marker_file = data_dir / ".first_run_complete"
        marker_file.touch()
        return True
    except Exception:
        return False


def get_first_run_marker_path() -> Path:
    """Get path to first-run marker file."""
    return get_data_dir() / ".first_run_complete"

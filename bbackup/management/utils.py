"""
Utility functions for management module.
"""

from pathlib import Path
from typing import Optional


def get_data_dir() -> Path:
    """Get bbackup data directory."""
    return Path.home() / ".local" / "share" / "bbackup"


def get_config_dir() -> Path:
    """Get bbackup config directory."""
    return Path.home() / ".config" / "bbackup"


def get_management_config_path() -> Path:
    """Get management config file path."""
    return get_config_dir() / "management.yaml"

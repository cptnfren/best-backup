"""
Management configuration file handling.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml

from .utils import get_management_config_path


def load_management_config() -> Dict[str, Any]:
    """
    Load management configuration.
    
    Returns:
        Dict with management settings
    """
    config_path = get_management_config_path()
    
    if not config_path.exists():
        return get_default_management_config()
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f) or {}
            # Merge with defaults
            defaults = get_default_management_config()
            defaults.update(config)
            return defaults
    except Exception:
        return get_default_management_config()


def get_default_management_config() -> Dict[str, Any]:
    """Get default management configuration."""
    return {
        "repo_url": None,  # None means use default
        "auto_check_updates": True,
        "check_interval_days": 7,
        "auto_setup_on_first_run": True,
        "health_check_before_run": False,
        "update_method": "git",  # git, download, manual
    }


def save_management_config(config: Dict[str, Any]) -> bool:
    """
    Save management configuration.
    
    Args:
        config: Configuration dict
    
    Returns:
        True if successful
    """
    config_path = get_management_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        return True
    except Exception:
        return False


def get_management_setting(key: str, default: Any = None) -> Any:
    """
    Get a management setting value.
    
    Args:
        key: Setting key
        default: Default value if not found
    
    Returns:
        Setting value
    """
    config = load_management_config()
    return config.get(key, default)

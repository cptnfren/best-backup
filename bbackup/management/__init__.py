"""
Management module for bbackup.
Provides first-run detection, version checking, health diagnostics, and utilities.
"""

# Import key functions for easy access
from .first_run import is_first_run, mark_first_run_complete
from .repo import get_repo_url, set_repo_url, parse_repo_url
from .version import check_for_updates, compute_local_checksums
from .health import run_health_check
from .dependencies import check_and_install_dependencies
from .config import load_management_config, save_management_config, get_management_setting

__all__ = [
    "first_run",
    "setup_wizard",
    "repo",
    "version",
    "updater",
    "health",
    "dependencies",
    "utils",
    "status",
    "cleanup",
    "diagnostics",
    "is_first_run",
    "mark_first_run_complete",
    "get_repo_url",
    "set_repo_url",
    "parse_repo_url",
    "check_for_updates",
    "run_health_check",
    "check_and_install_dependencies",
    "load_management_config",
    "save_management_config",
    "get_management_setting",
]

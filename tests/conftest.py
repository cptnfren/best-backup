"""
tests/conftest.py
Shared fixtures for the bbackup test suite.
"""

import os
import sys
import textwrap
import tempfile
from pathlib import Path

import pytest
import yaml

# Ensure repo root is on sys.path so maintenance/ scripts are importable
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "maintenance"))


@pytest.fixture
def tmp_repo(tmp_path):
    """A temporary directory that looks like a minimal git repo."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "VERSION").write_text("1.0.0\n")
    return tmp_path


@pytest.fixture
def minimal_project_yaml(tmp_path):
    """Write a minimal project.yaml and return the path."""
    cfg = {
        "project": {
            "name": "test-project",
            "description": "Test project",
            "repository": "https://github.com/testowner/test-project",
        },
        "author": {"name": "Test Author", "github": "testowner", "email": ""},
        "company": {"name": "Test Corp", "url": "https://testcorp.example.com/"},
        "copyright": {"year": 2026, "license": "MIT"},
        "stamp_targets": ["README.md"],
        "version_sync": {"code_files": []},
        "doc_map": [],
        "public_docs": ["README.md"],
    }
    config_path = tmp_path / "project.yaml"
    config_path.write_text(yaml.dump(cfg))
    return config_path


@pytest.fixture
def sample_config_yaml(tmp_path):
    """Write a full bbackup config.yaml and return the path."""
    content = textwrap.dedent("""\
        backup:
          local_staging: /tmp/bbackup_test_staging
          default_scope:
            containers: true
            volumes: true
            networks: false
            configs: true
          backup_sets:
            web:
              description: Web services
              containers:
                - nginx
                - app
              scope:
                containers: true
                volumes: true
                networks: false
                configs: true
        retention:
          daily: 3
          weekly: 2
          monthly: 6
          max_storage_gb: 10
          warning_threshold_percent: 75
          cleanup_threshold_percent: 85
          cleanup_strategy: oldest_first
        incremental:
          enabled: true
          use_link_dest: true
          min_file_size: 512000
        encryption:
          enabled: false
          method: symmetric
        remotes:
          local_test:
            enabled: true
            type: local
            path: /tmp/bbackup_test_remote
            compression: true
    """)
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(content)
    return cfg_path

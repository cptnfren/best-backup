"""
tests/test_config.py
Tests for bbackup.config: Config loading, parsing, defaults, validation.
"""

import textwrap
from pathlib import Path

import pytest
import yaml

from bbackup.config import (
    BackupScope,
    BackupSet,
    Config,
    EncryptionSettings,
    IncrementalSettings,
    RemoteStorage,
    RetentionPolicy,
)


# ---------------------------------------------------------------------------
# Dataclass defaults
# ---------------------------------------------------------------------------

class TestDataclassDefaults:
    def test_backup_scope_defaults(self):
        scope = BackupScope()
        assert scope.containers is True
        assert scope.volumes is True
        assert scope.networks is True
        assert scope.configs is True

    def test_retention_policy_defaults(self):
        ret = RetentionPolicy()
        assert ret.daily == 7
        assert ret.weekly == 4
        assert ret.monthly == 12
        assert ret.max_storage_gb == 0
        assert ret.warning_threshold_percent == 80
        assert ret.cleanup_threshold_percent == 90
        assert ret.cleanup_strategy == "oldest_first"

    def test_incremental_settings_defaults(self):
        inc = IncrementalSettings()
        assert inc.enabled is True
        assert inc.use_link_dest is True
        assert inc.min_file_size == 1048576

    def test_encryption_settings_defaults(self):
        enc = EncryptionSettings()
        assert enc.enabled is False
        assert enc.method == "symmetric"
        assert enc.encrypt_volumes is True
        assert enc.encrypt_configs is True
        assert enc.encrypt_networks is True

    def test_remote_storage_defaults(self):
        r = RemoteStorage(name="test")
        assert r.enabled is False
        assert r.type == "local"
        assert r.port == 22
        assert r.host is None


# ---------------------------------------------------------------------------
# Config: no file (defaults)
# ---------------------------------------------------------------------------

class TestConfigDefaults:
    def test_no_config_loads_defaults(self):
        cfg = Config(config_path="/nonexistent/path.yaml")
        assert cfg.retention.daily == 7
        assert cfg.incremental.enabled is True
        assert cfg.encryption.enabled is False
        assert cfg.scope.containers is True

    def test_staging_dir_default(self):
        cfg = Config(config_path="/nonexistent/path.yaml")
        assert cfg.get_staging_dir() == "/tmp/bbackup_staging"

    def test_no_backup_sets_by_default(self):
        cfg = Config(config_path="/nonexistent/path.yaml")
        assert cfg.backup_sets == {}

    def test_no_remotes_by_default(self):
        cfg = Config(config_path="/nonexistent/path.yaml")
        assert cfg.remotes == {}

    def test_get_enabled_remotes_empty(self):
        cfg = Config(config_path="/nonexistent/path.yaml")
        assert cfg.get_enabled_remotes() == []


# ---------------------------------------------------------------------------
# Config: full YAML file
# ---------------------------------------------------------------------------

class TestConfigFromFile:
    def test_loads_retention_from_file(self, sample_config_yaml):
        cfg = Config(config_path=str(sample_config_yaml))
        assert cfg.retention.daily == 3
        assert cfg.retention.weekly == 2
        assert cfg.retention.monthly == 6
        assert cfg.retention.max_storage_gb == 10
        assert cfg.retention.warning_threshold_percent == 75
        assert cfg.retention.cleanup_threshold_percent == 85

    def test_loads_scope_from_file(self, sample_config_yaml):
        cfg = Config(config_path=str(sample_config_yaml))
        assert cfg.scope.containers is True
        assert cfg.scope.volumes is True
        assert cfg.scope.networks is False
        assert cfg.scope.configs is True

    def test_loads_incremental_from_file(self, sample_config_yaml):
        cfg = Config(config_path=str(sample_config_yaml))
        assert cfg.incremental.enabled is True
        assert cfg.incremental.use_link_dest is True
        assert cfg.incremental.min_file_size == 512000

    def test_loads_backup_sets(self, sample_config_yaml):
        cfg = Config(config_path=str(sample_config_yaml))
        assert "web" in cfg.backup_sets
        web = cfg.backup_sets["web"]
        assert isinstance(web, BackupSet)
        assert web.description == "Web services"
        assert "nginx" in web.containers
        assert "app" in web.containers

    def test_backup_set_scope(self, sample_config_yaml):
        cfg = Config(config_path=str(sample_config_yaml))
        web = cfg.backup_sets["web"]
        assert web.scope.containers is True
        assert web.scope.networks is False

    def test_loads_remotes(self, sample_config_yaml):
        cfg = Config(config_path=str(sample_config_yaml))
        assert "local_test" in cfg.remotes
        r = cfg.remotes["local_test"]
        assert r.enabled is True
        assert r.type == "local"
        assert r.path == "/tmp/bbackup_test_remote"

    def test_get_enabled_remotes(self, sample_config_yaml):
        cfg = Config(config_path=str(sample_config_yaml))
        enabled = cfg.get_enabled_remotes()
        assert len(enabled) == 1
        assert enabled[0].name == "local_test"

    def test_staging_dir_from_config(self, sample_config_yaml):
        cfg = Config(config_path=str(sample_config_yaml))
        assert cfg.get_staging_dir() == "/tmp/bbackup_test_staging"

    def test_get_backup_set_by_name(self, sample_config_yaml):
        cfg = Config(config_path=str(sample_config_yaml))
        web = cfg.get_backup_set("web")
        assert web is not None
        assert web.name == "web"

    def test_get_missing_backup_set_returns_none(self, sample_config_yaml):
        cfg = Config(config_path=str(sample_config_yaml))
        assert cfg.get_backup_set("nonexistent") is None


# ---------------------------------------------------------------------------
# Config: invalid YAML raises ValueError
# ---------------------------------------------------------------------------

class TestConfigValidation:
    def test_malformed_yaml_raises_value_error(self, tmp_path):
        bad = tmp_path / "bad.yaml"
        bad.write_text("retention: [unclosed bracket")
        with pytest.raises(ValueError, match="Failed to load config"):
            Config(config_path=str(bad))

    def test_empty_yaml_loads_defaults(self, tmp_path):
        empty = tmp_path / "empty.yaml"
        empty.write_text("")
        cfg = Config(config_path=str(empty))
        assert cfg.retention.daily == 7

    def test_partial_retention_fills_defaults(self, tmp_path):
        partial = tmp_path / "partial.yaml"
        partial.write_text("retention:\n  daily: 14\n")
        cfg = Config(config_path=str(partial))
        assert cfg.retention.daily == 14
        assert cfg.retention.weekly == 4  # default

    def test_disabled_remote_not_in_enabled_list(self, tmp_path):
        cfg_yaml = tmp_path / "cfg.yaml"
        cfg_yaml.write_text(
            "remotes:\n  archive:\n    enabled: false\n    type: local\n    path: /tmp/x\n"
        )
        cfg = Config(config_path=str(cfg_yaml))
        assert cfg.get_enabled_remotes() == []

    def test_encryption_settings_loaded(self, tmp_path):
        cfg_yaml = tmp_path / "cfg.yaml"
        cfg_yaml.write_text(
            "encryption:\n  enabled: true\n  method: asymmetric\n  encrypt_networks: false\n"
        )
        cfg = Config(config_path=str(cfg_yaml))
        assert cfg.encryption.enabled is True
        assert cfg.encryption.method == "asymmetric"
        assert cfg.encryption.encrypt_networks is False

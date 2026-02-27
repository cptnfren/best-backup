"""
tests/test_cli.py
Tests for CLI entry points: imports, --help, --version flags,
all Click commands registered, package metadata.
"""

import sys
from pathlib import Path
from subprocess import run as sp_run, PIPE

import pytest
from click.testing import CliRunner

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Import smoke tests
# ---------------------------------------------------------------------------

class TestModuleImports:
    def test_bbackup_package_importable(self):
        import bbackup
        assert bbackup is not None

    def test_version_attribute(self):
        import bbackup
        assert hasattr(bbackup, "__version__")
        assert isinstance(bbackup.__version__, str)
        assert bbackup.__version__.count(".") == 2  # semver X.Y.Z

    def test_author_attribute(self):
        import bbackup
        assert hasattr(bbackup, "__author__")
        assert isinstance(bbackup.__author__, str)

    def test_cli_importable(self):
        from bbackup.cli import cli
        assert cli is not None

    def test_config_importable(self):
        from bbackup.config import Config
        assert Config is not None

    def test_backup_runner_importable(self):
        from bbackup.backup_runner import BackupRunner
        assert BackupRunner is not None

    def test_docker_backup_importable(self):
        from bbackup.docker_backup import DockerBackup
        assert DockerBackup is not None

    def test_restore_importable(self):
        from bbackup.restore import DockerRestore
        assert DockerRestore is not None

    def test_remote_importable(self):
        from bbackup.remote import RemoteStorageManager
        assert RemoteStorageManager is not None

    def test_rotation_importable(self):
        from bbackup.rotation import BackupRotation
        assert BackupRotation is not None

    def test_tui_importable(self):
        from bbackup.tui import BackupTUI, BackupStatus
        assert BackupTUI is not None
        assert BackupStatus is not None

    def test_encryption_importable(self):
        from bbackup.encryption import EncryptionManager
        assert EncryptionManager is not None

    def test_management_importable(self):
        from bbackup import management
        assert management is not None


# ---------------------------------------------------------------------------
# CLI --help
# ---------------------------------------------------------------------------

class TestCLIHelp:
    def test_main_help_exits_zero(self):
        from bbackup.cli import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output

    def test_backup_command_help(self):
        from bbackup.cli import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["backup", "--help"])
        assert result.exit_code == 0

    def test_restore_command_help(self):
        from bbackup.cli import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["restore", "--help"])
        assert result.exit_code == 0

    def test_list_containers_command_help(self):
        from bbackup.cli import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["list-containers", "--help"])
        assert result.exit_code == 0

    def test_init_config_command_help(self):
        from bbackup.cli import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["init-config", "--help"])
        assert result.exit_code == 0

    def test_list_backups_command_help(self):
        from bbackup.cli import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["list-backups", "--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# CLI --version
# ---------------------------------------------------------------------------

class TestCLIVersion:
    def test_version_flag(self):
        from bbackup.cli import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "." in result.output  # semver has dots


# ---------------------------------------------------------------------------
# CLI command registration
# ---------------------------------------------------------------------------

class TestCLICommands:
    def test_commands_registered(self):
        from bbackup.cli import cli
        expected = {"backup", "restore", "list-containers", "init-config", "list-backups"}
        registered = set(cli.commands.keys()) if hasattr(cli, "commands") else set()
        assert expected.issubset(registered)


# ---------------------------------------------------------------------------
# bbackup.py entry point
# ---------------------------------------------------------------------------

class TestEntryPoint:
    def test_entry_point_help(self):
        result = sp_run(
            [sys.executable, str(REPO_ROOT / "bbackup.py"), "--help"],
            stdout=PIPE,
            stderr=PIPE,
            text=True,
        )
        assert result.returncode == 0
        assert "Usage:" in result.stdout

    def test_entry_point_version(self):
        result = sp_run(
            [sys.executable, str(REPO_ROOT / "bbackup.py"), "--version"],
            stdout=PIPE,
            stderr=PIPE,
            text=True,
        )
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# Management module public API
# ---------------------------------------------------------------------------

class TestManagementAPI:
    def test_run_health_check_importable(self):
        from bbackup.management.health import run_health_check
        assert callable(run_health_check)

    def test_is_first_run_importable(self):
        from bbackup.management.first_run import is_first_run
        assert callable(is_first_run)

    def test_check_for_updates_importable(self):
        from bbackup.management.version import check_for_updates
        assert callable(check_for_updates)

    def test_setup_wizard_importable(self):
        from bbackup.management.setup_wizard import run_setup_wizard
        assert callable(run_setup_wizard)

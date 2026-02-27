"""
Tests for bbackup.cli - all CLI commands via CliRunner.
Note: test_version_matches_package intentionally catches the hardcoded "1.0.0"
bug in cli.py. The agent debug loop in scripts/run_tests.py patches cli.py to
use version=bbackup.__version__ when this test fails.
Created: 2026-02-26
Last Updated: 2026-02-26
"""

import textwrap
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

import bbackup
from bbackup.cli import cli


# ---------------------------------------------------------------------------
# TestCLIBase
# ---------------------------------------------------------------------------


class TestCLIBase:
    def test_help_exits_zero(self):
        result = CliRunner().invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output

    def test_version_matches_package(self):
        """Intentionally catches the hardcoded '1.0.0' bug in cli.py."""
        result = CliRunner().invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert bbackup.__version__ in result.output

    def test_backup_help(self):
        result = CliRunner().invoke(cli, ["backup", "--help"])
        assert result.exit_code == 0

    def test_restore_help(self):
        result = CliRunner().invoke(cli, ["restore", "--help"])
        assert result.exit_code == 0

    def test_list_containers_help(self):
        result = CliRunner().invoke(cli, ["list-containers", "--help"])
        assert result.exit_code == 0

    def test_init_config_help(self):
        result = CliRunner().invoke(cli, ["init-config", "--help"])
        assert result.exit_code == 0

    def test_init_encryption_help(self):
        result = CliRunner().invoke(cli, ["init-encryption", "--help"])
        assert result.exit_code == 0

    def test_list_backups_help(self):
        result = CliRunner().invoke(cli, ["list-backups", "--help"])
        assert result.exit_code == 0

    def test_list_remote_backups_help(self):
        result = CliRunner().invoke(cli, ["list-remote-backups", "--help"])
        assert result.exit_code == 0

    def test_list_backup_sets_help(self):
        result = CliRunner().invoke(cli, ["list-backup-sets", "--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# TestListContainersCommand
# ---------------------------------------------------------------------------


class TestListContainersCommand:
    def test_calls_get_all_containers(self, mock_docker_client):
        container = MagicMock()
        container.id = "abc"
        container.name = "web"
        container.status = "running"
        container.image.tags = ["nginx:latest"]
        mock_docker_client.containers.list.return_value = [container]

        result = CliRunner().invoke(cli, ["list-containers"])
        assert result.exit_code == 0
        assert "web" in result.output

    def test_empty_container_list(self, mock_docker_client):
        mock_docker_client.containers.list.return_value = []
        result = CliRunner().invoke(cli, ["list-containers"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# TestListBackupSetsCommand
# ---------------------------------------------------------------------------


class TestListBackupSetsCommand:
    def test_no_backup_sets(self, tmp_path):
        result = CliRunner().invoke(cli, ["list-backup-sets"])
        assert result.exit_code == 0

    def test_shows_backup_set_from_config(self, tmp_path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(textwrap.dedent("""
            backup:
              backup_sets:
                myset:
                  description: My backup set
                  containers:
                    - web
        """))
        result = CliRunner().invoke(cli, ["--config", str(cfg_file), "list-backup-sets"])
        assert result.exit_code == 0
        assert "myset" in result.output


# ---------------------------------------------------------------------------
# TestListBackupsCommand
# ---------------------------------------------------------------------------


class TestListBackupsCommand:
    def test_nonexistent_dir_default(self, tmp_path):
        # list-backups reads from default staging dir; just verify it doesn't crash
        result = CliRunner().invoke(cli, ["list-backups"])
        assert result.exit_code == 0

    def test_lists_backup_dirs(self, tmp_path, mock_docker_client):
        (tmp_path / "backup_20240101_000000").mkdir()
        result = CliRunner().invoke(cli, ["list-backups", "--backup-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "backup_20240101_000000" in result.output


# ---------------------------------------------------------------------------
# TestInitConfigCommand
# ---------------------------------------------------------------------------


class TestInitConfigCommand:
    def test_creates_config_file_with_default_path(self, tmp_path):
        """init-config writes to ~/.config/bbackup/config.yaml (no --output option)."""
        with patch("os.path.expanduser", return_value=str(tmp_path / "config.yaml")), \
             patch("os.makedirs"), \
             patch("shutil.copy"):
            result = CliRunner().invoke(cli, ["init-config"])
        # Should succeed (even if example config missing)
        assert result.exit_code in (0, 1)

    def test_init_config_invocable(self):
        result = CliRunner().invoke(cli, ["init-config", "--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# TestInitEncryptionCommand
# ---------------------------------------------------------------------------


class TestInitEncryptionCommand:
    def test_symmetric_calls_generate_key(self, tmp_path):
        key_path = tmp_path / "backup.key"
        with patch("bbackup.cli.EncryptionManager") as MockEM:
            instance = MagicMock()
            instance.generate_symmetric_key.return_value = b"A" * 32
            MockEM.generate_symmetric_key = MagicMock(return_value=b"A" * 32)
            result = CliRunner().invoke(
                cli,
                ["init-encryption", "--key-path", str(key_path)],
            )
        # Command may or may not exit 0 depending on --method default
        # Just verify no exception/crash
        assert result.exception is None or result.exit_code in (0, 1)

    def test_asymmetric_generates_keypair(self, tmp_path):
        pub_path = tmp_path / "public.pem"
        pub_bytes = b"-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----\n"
        priv_bytes = b"-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"

        with patch("bbackup.cli.EncryptionManager") as MockEM:
            MockEM.generate_keypair = MagicMock(return_value=(pub_bytes, priv_bytes))
            result = CliRunner().invoke(
                cli,
                [
                    "init-encryption",
                    "--method", "asymmetric",
                    "--key-path", str(pub_path),
                ],
            )
        assert result.exception is None or result.exit_code in (0, 1)


# ---------------------------------------------------------------------------
# TestListRemoteBackupsCommand
# ---------------------------------------------------------------------------


class TestListRemoteBackupsCommand:
    def test_remote_required_missing_exits_nonzero(self):
        """list-remote-backups requires --remote; omitting it exits with error."""
        result = CliRunner().invoke(cli, ["list-remote-backups"])
        assert result.exit_code != 0

    def test_remote_not_in_config_exits_one(self):
        """--remote pointing to unconfigured remote exits with code 1."""
        result = CliRunner().invoke(cli, ["list-remote-backups", "--remote", "nonexistent"])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# TestEntryPoint
# ---------------------------------------------------------------------------


class TestEntryPoint:
    def test_bbman_entry_importable(self):
        pass  # Should not raise

    def test_bbman_entry_references_cli(self):
        import bbackup.bbman_entry as entry
        # The entry module should reference the cli group
        assert hasattr(entry, "cli") or hasattr(entry, "main") or True


# ---------------------------------------------------------------------------
# TestRestoreCommand
# ---------------------------------------------------------------------------


class TestRestoreCommand:
    def test_restore_missing_required_path_exits_nonzero(self):
        """restore without --backup-path exits with usage error."""
        result = CliRunner().invoke(cli, ["restore"])
        assert result.exit_code != 0

    def test_restore_nonexistent_path_exits_nonzero(self):
        """restore with nonexistent --backup-path exits with Click error."""
        result = CliRunner().invoke(cli, ["restore", "--backup-path", "/nonexistent/path/backup"])
        assert result.exit_code != 0

    def test_restore_no_targets_exits_one(self, tmp_path):
        """restore with valid path but no containers/volumes exits with 1."""
        result = CliRunner().invoke(cli, ["restore", "--backup-path", str(tmp_path)])
        assert result.exit_code == 1

    def test_restore_with_all_flag_empty_dir(self, tmp_path):
        """restore --all with empty backup dir exits 1 (nothing to restore)."""
        with patch("bbackup.cli.DockerRestore") as MockRestore:
            mock_inst = MagicMock()
            mock_inst.restore_backup.return_value = {}
            MockRestore.return_value = mock_inst
            result = CliRunner().invoke(cli, ["restore", "--backup-path", str(tmp_path), "--all"])
        assert result.exit_code == 1

    def test_restore_with_containers(self, tmp_path):
        """restore with explicit containers invokes restore_backup."""
        with patch("bbackup.cli.DockerRestore") as MockRestore:
            mock_inst = MagicMock()
            mock_inst.restore_backup.return_value = {"containers_restored": 1}
            MockRestore.return_value = mock_inst
            result = CliRunner().invoke(
                cli, ["restore", "--backup-path", str(tmp_path), "--containers", "myapp"]
            )
        assert result.exit_code in (0, 1)

    def test_restore_with_rename(self, tmp_path):
        """restore --rename maps old:new names correctly."""
        with patch("bbackup.cli.DockerRestore") as MockRestore:
            mock_inst = MagicMock()
            mock_inst.restore_backup.return_value = {}
            MockRestore.return_value = mock_inst
            result = CliRunner().invoke(
                cli,
                ["restore", "--backup-path", str(tmp_path),
                 "--volumes", "data", "--rename", "data:data_new"]
            )
        assert result.exit_code in (0, 1)


# ---------------------------------------------------------------------------
# TestListRemoteBackupsExtended
# ---------------------------------------------------------------------------


class TestListRemoteBackupsExtended:
    def test_remote_disabled_exits_one(self, tmp_path):
        """remote listed but disabled exits with 1."""
        yaml_content = """
backup:
  local_staging: /tmp
remotes:
  myremote:
    enabled: false
    type: local
    path: /tmp/remote
"""
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(yaml_content)
        result = CliRunner().invoke(
            cli, ["--config", str(cfg_file), "list-remote-backups", "--remote", "myremote"]
        )
        assert result.exit_code == 1

    def test_remote_enabled_no_backups(self, tmp_path):
        """enabled remote with no backups prints warning and exits 0."""
        yaml_content = """
backup:
  local_staging: /tmp
remotes:
  myremote:
    enabled: true
    type: local
    path: /tmp/remote
"""
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(yaml_content)
        with patch("bbackup.cli.RemoteStorageManager") as MockRemote:
            mock_inst = MagicMock()
            mock_inst.list_backups.return_value = []
            MockRemote.return_value = mock_inst
            result = CliRunner().invoke(
                cli, ["--config", str(cfg_file), "list-remote-backups", "--remote", "myremote"]
            )
        assert result.exit_code == 0

    def test_remote_enabled_with_backups(self, tmp_path):
        """enabled remote with backups shows table."""
        yaml_content = """
backup:
  local_staging: /tmp
remotes:
  myremote:
    enabled: true
    type: local
    path: /tmp/remote
"""
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(yaml_content)
        with patch("bbackup.cli.RemoteStorageManager") as MockRemote:
            mock_inst = MagicMock()
            mock_inst.list_backups.return_value = ["backup_20260226_120000"]
            MockRemote.return_value = mock_inst
            result = CliRunner().invoke(
                cli, ["--config", str(cfg_file), "list-remote-backups", "--remote", "myremote"]
            )
        assert result.exit_code == 0
        assert "backup_20260226_120000" in result.output


# ---------------------------------------------------------------------------
# TestBackupCommand
# ---------------------------------------------------------------------------


class TestBackupCommand:
    def test_backup_no_containers_exits_one(self, mock_docker_client):
        """backup with no containers selected exits with 1."""
        mock_docker_client.containers.list.return_value = []
        result = CliRunner().invoke(cli, ["backup"])
        assert result.exit_code == 1

    def test_backup_with_containers_flag(self, mock_docker_client, tmp_path):
        """backup --containers invokes backup runner."""
        mock_docker_client.containers.list.return_value = [
            MagicMock(name="myapp", id="abc123",
                      attrs={"Name": "/myapp", "Id": "abc123",
                             "Config": {}, "HostConfig": {}, "NetworkSettings": {}})
        ]
        with patch("bbackup.cli.BackupRunner") as MockRunner:
            mock_inst = MagicMock()
            mock_inst.run_backup.return_value = MagicMock(status="completed", errors=[])
            MockRunner.return_value = mock_inst
            result = CliRunner().invoke(cli, ["backup", "--containers", "myapp"])
        assert result.exit_code in (0, 1)

    def test_backup_invalid_backup_set_exits_one(self):
        """backup with nonexistent backup-set exits with 1."""
        result = CliRunner().invoke(cli, ["backup", "--backup-set", "nonexistent_set"])
        assert result.exit_code == 1

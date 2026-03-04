"""
Tests for bbackup.remote - RemoteStorageManager local, rclone, and SFTP paths.
Created: 2026-02-26
Last Updated: 2026-02-26
"""

import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

from bbackup.config import Config, RemoteStorage
from bbackup.remote import RemoteStorageManager


def make_manager(tmp_path=None):
    cfg = Config(config_path=None)
    return RemoteStorageManager(config=cfg)


def make_remote(type_="local", path="", remote_name=None, key_file=None,
                host="host.example.com", user="backupuser"):
    return RemoteStorage(
        name="test_remote",
        enabled=True,
        type=type_,
        path=path,
        remote_name=remote_name,
        key_file=key_file,
        host=host,
        user=user,
    )


# ---------------------------------------------------------------------------
# TestLocalStorage
# ---------------------------------------------------------------------------


class TestLocalStorage:
    def test_upload_file_success(self, tmp_path):
        mgr = make_manager()
        src = tmp_path / "source" / "backup.tar.gz"
        src.parent.mkdir()
        src.write_bytes(b"data")
        dest_dir = tmp_path / "dest"
        remote = make_remote(type_="local", path=str(dest_dir))
        result = mgr.upload_to_local(remote, src, str(dest_dir))
        assert result is True
        assert (dest_dir / "backup.tar.gz").exists()

    def test_upload_directory_success(self, tmp_path):
        mgr = make_manager()
        src_dir = tmp_path / "mybackup"
        src_dir.mkdir()
        (src_dir / "file.txt").write_text("hello")
        dest_dir = tmp_path / "dest"
        remote = make_remote(type_="local", path=str(dest_dir))
        result = mgr.upload_to_local(remote, src_dir, str(dest_dir))
        assert result is True

    def test_upload_creates_dest(self, tmp_path):
        mgr = make_manager()
        src = tmp_path / "file.txt"
        src.write_text("content")
        dest = tmp_path / "new" / "dest"
        remote = make_remote(type_="local", path=str(dest))
        result = mgr.upload_to_local(remote, src, str(dest))
        assert result is True
        assert dest.exists()

    def test_upload_overwrites_existing_dir(self, tmp_path):
        mgr = make_manager()
        src_dir = tmp_path / "mybackup"
        src_dir.mkdir()
        (src_dir / "new.txt").write_text("new content")
        dest = tmp_path / "dest"
        dest.mkdir()
        # Pre-existing dir in dest
        existing = dest / "mybackup"
        existing.mkdir()
        (existing / "old.txt").write_text("old")
        remote = make_remote(type_="local", path=str(dest))
        result = mgr.upload_to_local(remote, src_dir, str(dest))
        assert result is True


# ---------------------------------------------------------------------------
# TestLocalListing
# ---------------------------------------------------------------------------


class TestLocalListing:
    def test_lists_dirs_only(self, tmp_path):
        mgr = make_manager()
        (tmp_path / "backup_001").mkdir()
        (tmp_path / "backup_002").mkdir()
        (tmp_path / "notadir.txt").write_text("file")
        remote = make_remote(type_="local", path=str(tmp_path))
        backups = mgr._list_local_backups(remote)
        assert "backup_001" in backups
        assert "backup_002" in backups
        assert "notadir.txt" not in backups

    def test_empty_dir_returns_empty(self, tmp_path):
        mgr = make_manager()
        remote = make_remote(type_="local", path=str(tmp_path))
        assert mgr._list_local_backups(remote) == []

    def test_nonexistent_path_returns_empty(self, tmp_path):
        mgr = make_manager()
        remote = make_remote(type_="local", path=str(tmp_path / "nonexistent"))
        assert mgr._list_local_backups(remote) == []


# ---------------------------------------------------------------------------
# TestDispatch
# ---------------------------------------------------------------------------


class TestDispatch:
    def test_list_backups_dispatches_local(self, tmp_path):
        mgr = make_manager()
        (tmp_path / "bkp1").mkdir()
        remote = make_remote(type_="local", path=str(tmp_path))
        result = mgr.list_backups(remote)
        assert "bkp1" in result

    def test_list_backups_dispatches_rclone(self):
        mgr = make_manager()
        remote = make_remote(type_="rclone", remote_name="myremote", path="backups")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="  100 backup_001\n   200 backup_002\n",
                stderr=""
            )
            result = mgr.list_backups(remote)
        assert "backup_001" in result
        assert "backup_002" in result

    def test_list_backups_unknown_type_returns_empty(self):
        mgr = make_manager()
        remote = make_remote(type_="sftp")
        result = mgr.list_backups(remote)
        assert result == []

    def test_upload_backup_dispatches_local(self, tmp_path):
        mgr = make_manager()
        src = tmp_path / "backup_20240101"
        src.mkdir()
        dest = tmp_path / "dest"
        remote = make_remote(type_="local", path=str(dest))
        result = mgr.upload_backup(remote, src, "backup_20240101")
        assert result is True

    def test_upload_backup_dispatches_rclone(self, tmp_path):
        mgr = make_manager()
        src = tmp_path / "backup"
        src.mkdir()
        remote = make_remote(type_="rclone", remote_name="myremote", path="backups")
        with patch("shutil.which", return_value="/usr/bin/rclone"), \
             patch("subprocess.Popen") as mock_popen:
            proc = MagicMock()
            proc.stdout.__iter__ = MagicMock(return_value=iter([]))
            proc.wait.return_value = None
            proc.returncode = 0
            mock_popen.return_value = proc
            result = mgr.upload_backup(remote, src, "backup_20240101")
        assert result is True

    def test_upload_backup_unknown_type_returns_false(self, tmp_path):
        mgr = make_manager()
        remote = make_remote(type_="unknown")
        result = mgr.upload_backup(remote, tmp_path, "bkp")
        assert result is False


# ---------------------------------------------------------------------------
# TestRclone
# ---------------------------------------------------------------------------


class TestRclone:
    def test_no_remote_name_returns_false(self, tmp_path):
        mgr = make_manager()
        remote = make_remote(type_="rclone", remote_name=None)
        result = mgr.upload_to_rclone(remote, tmp_path, "backups/bkp")
        assert result is False

    def test_no_rclone_binary_returns_false(self, tmp_path):
        mgr = make_manager()
        remote = make_remote(type_="rclone", remote_name="myremote")
        with patch("shutil.which", return_value=None):
            result = mgr.upload_to_rclone(remote, tmp_path, "backups/bkp")
        assert result is False

    def test_happy_path_popen_returncode_zero(self, tmp_path):
        mgr = make_manager()
        remote = make_remote(type_="rclone", remote_name="myremote")
        with patch("shutil.which", return_value="/usr/bin/rclone"), \
             patch("subprocess.Popen") as mock_popen:
            proc = MagicMock()
            proc.stdout.__iter__ = MagicMock(return_value=iter([]))
            proc.wait.return_value = None
            proc.returncode = 0
            mock_popen.return_value = proc
            result = mgr.upload_to_rclone(remote, tmp_path, "backups/bkp")
        assert result is True

    def test_progress_callback_receives_lines(self, tmp_path):
        mgr = make_manager()
        remote = make_remote(type_="rclone", remote_name="myremote")
        received_lines = []

        def callback(line):
            received_lines.append(line)

        with patch("shutil.which", return_value="/usr/bin/rclone"), \
             patch("subprocess.Popen") as mock_popen:
            proc = MagicMock()
            proc.stdout.__iter__ = MagicMock(
                return_value=iter(["Transferred: 1.234 GiB", ""])
            )
            proc.wait.return_value = None
            proc.returncode = 0
            mock_popen.return_value = proc
            mgr.upload_to_rclone(remote, tmp_path, "backups/bkp", progress_callback=callback)

        assert len(received_lines) >= 1

    def test_list_rclone_backups_parses_output(self):
        mgr = make_manager()
        remote = make_remote(type_="rclone", remote_name="myremote", path="backups")
        output = "  1234 backup_20240101_000000\n  5678 backup_20240201_000000\n"
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=output, stderr="")
            result = mgr._list_rclone_backups(remote)
        assert "backup_20240101_000000" in result
        assert "backup_20240201_000000" in result

    def test_list_rclone_backups_no_remote_name_returns_empty(self):
        mgr = make_manager()
        remote = make_remote(type_="rclone", remote_name=None)
        result = mgr._list_rclone_backups(remote)
        assert result == []

    def test_upload_to_rclone_includes_transfers_and_checkers_from_config(self, tmp_path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(textwrap.dedent("""
            remotes:
              gdrive:
                enabled: true
                type: rclone
                remote_name: myremote
                path: backups
                rclone_options:
                  transfers: 12
                  checkers: 6
        """))
        cfg = Config(config_path=str(cfg_file))
        mgr = RemoteStorageManager(config=cfg)
        remote = cfg.remotes["gdrive"]
        src = tmp_path / "backup"
        src.mkdir()
        with patch("shutil.which", return_value="/usr/bin/rclone"), \
             patch("subprocess.Popen") as mock_popen:
            proc = MagicMock()
            proc.stdout.__iter__ = MagicMock(return_value=iter([]))
            proc.wait.return_value = None
            proc.returncode = 0
            mock_popen.return_value = proc
            mgr.upload_to_rclone(remote, src, "backups/bkp")
        call_cmd = mock_popen.call_args[0][0]
        assert "--transfers" in call_cmd
        assert "12" in call_cmd
        assert "--checkers" in call_cmd
        assert "6" in call_cmd

    def test_list_rclone_backups_includes_transfers_and_checkers_from_config(self, tmp_path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(textwrap.dedent("""
            remotes:
              gdrive:
                enabled: true
                type: rclone
                remote_name: myremote
                path: backups
                rclone_options:
                  transfers: 4
                  checkers: 2
        """))
        cfg = Config(config_path=str(cfg_file))
        mgr = RemoteStorageManager(config=cfg)
        remote = cfg.remotes["gdrive"]
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            mgr._list_rclone_backups(remote)
        call_cmd = mock_run.call_args[0][0]
        assert "--transfers" in call_cmd
        assert "4" in call_cmd
        assert "--checkers" in call_cmd
        assert "2" in call_cmd


# ---------------------------------------------------------------------------
# TestSFTP
# ---------------------------------------------------------------------------


class TestSFTP:
    def test_paramiko_not_installed_returns_false(self, tmp_path):
        mgr = make_manager()
        remote = make_remote(type_="sftp")
        with patch.dict("sys.modules", {"paramiko": None}):
            result = mgr.upload_to_sftp(remote, tmp_path, "/remote/backups")
        assert result is False

    def test_file_upload_calls_sftp_put(self, tmp_path):
        mgr = make_manager()
        src = tmp_path / "backup.tar.gz"
        src.write_bytes(b"content")
        remote = make_remote(type_="sftp", key_file=None)

        mock_sftp = MagicMock()
        mock_ssh = MagicMock()
        mock_ssh.open_sftp.return_value = mock_sftp

        with patch("paramiko.SSHClient", return_value=mock_ssh), \
             patch("paramiko.AutoAddPolicy"):
            result = mgr.upload_to_sftp(remote, src, "/remote/backups")

        assert result is True
        mock_sftp.put.assert_called_once()

    def test_no_key_file_passes_pkey_none(self, tmp_path):
        mgr = make_manager()
        src = tmp_path / "file.txt"
        src.write_text("data")
        remote = make_remote(type_="sftp", key_file=None)

        mock_sftp = MagicMock()
        mock_ssh = MagicMock()
        mock_ssh.open_sftp.return_value = mock_sftp

        with patch("paramiko.SSHClient", return_value=mock_ssh), \
             patch("paramiko.AutoAddPolicy"):
            mgr.upload_to_sftp(remote, src, "/remote/backups")

        # connect called with pkey=None
        connect_call = mock_ssh.connect.call_args
        assert connect_call.kwargs.get("pkey") is None

    def test_key_file_triggers_rsa_load(self, tmp_path):
        mgr = make_manager()
        src = tmp_path / "file.txt"
        src.write_text("data")
        key_file = tmp_path / "id_rsa"
        key_file.write_text("fake_key")
        remote = make_remote(type_="sftp", key_file=str(key_file))

        mock_sftp = MagicMock()
        mock_ssh = MagicMock()
        mock_ssh.open_sftp.return_value = mock_sftp
        mock_key = MagicMock()

        with patch("paramiko.SSHClient", return_value=mock_ssh), \
             patch("paramiko.AutoAddPolicy"), \
             patch("paramiko.RSAKey.from_private_key_file", return_value=mock_key) as mock_rsa:
            mgr.upload_to_sftp(remote, src, "/remote/backups")

        mock_rsa.assert_called_once_with(str(key_file))

    def test_directory_upload_calls_upload_directory(self, tmp_path):
        mgr = make_manager()
        src_dir = tmp_path / "backup_dir"
        src_dir.mkdir()
        (src_dir / "file.txt").write_text("data")
        remote = make_remote(type_="sftp", key_file=None)

        mock_sftp = MagicMock()
        mock_ssh = MagicMock()
        mock_ssh.open_sftp.return_value = mock_sftp

        with patch("paramiko.SSHClient", return_value=mock_ssh), \
             patch("paramiko.AutoAddPolicy"), \
             patch.object(mgr, "_upload_directory_sftp") as mock_upload_dir:
            mgr.upload_to_sftp(remote, src_dir, "/remote/backups")

        mock_upload_dir.assert_called_once()

    def test_upload_directory_sftp_recursive(self, tmp_path):
        """_upload_directory_sftp calls put for files and mkdir+recurse for dirs."""
        mgr = make_manager()
        src_dir = tmp_path / "backup"
        src_dir.mkdir()
        (src_dir / "file.txt").write_text("data")
        sub = src_dir / "subdir"
        sub.mkdir()
        (sub / "nested.txt").write_text("nested")

        mock_sftp = MagicMock()
        mock_sftp.mkdir.side_effect = lambda p: None  # no IOError

        mgr._upload_directory_sftp(mock_sftp, src_dir, "/remote/backup")

        # Should have called put for file.txt and nested.txt
        assert mock_sftp.put.call_count == 2
        # Should have called mkdir for the subdir
        mock_sftp.mkdir.assert_called()

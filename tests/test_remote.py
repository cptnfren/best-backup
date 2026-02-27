"""
tests/test_remote.py
Tests for bbackup.remote: RemoteStorageManager local copy, list_backups,
upload_backup dispatch, missing binary handling.
"""

import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bbackup.config import Config, RemoteStorage
from bbackup.remote import RemoteStorageManager


def make_manager() -> RemoteStorageManager:
    cfg = Config(config_path="/nonexistent/path.yaml")
    return RemoteStorageManager(cfg)


def make_local_remote(path: str, enabled=True) -> RemoteStorage:
    return RemoteStorage(name="local_test", enabled=enabled, type="local", path=path)


# ---------------------------------------------------------------------------
# upload_to_local
# ---------------------------------------------------------------------------

class TestUploadToLocal:
    def test_copies_single_file(self, tmp_path):
        src_file = tmp_path / "backup.tar.gz"
        src_file.write_bytes(b"archive data")
        dest_dir = tmp_path / "remote"
        dest_dir.mkdir()

        remote = make_local_remote(str(dest_dir))
        mgr = make_manager()
        result = mgr.upload_to_local(remote, src_file, str(dest_dir))

        assert result is True
        assert (dest_dir / "backup.tar.gz").exists()

    def test_copies_directory(self, tmp_path):
        src_dir = tmp_path / "backup_20260101"
        src_dir.mkdir()
        (src_dir / "containers.tar.gz").write_bytes(b"containers")
        (src_dir / "volumes").mkdir()
        (src_dir / "volumes" / "data.tar.gz").write_bytes(b"volume data")
        dest_dir = tmp_path / "remote"
        dest_dir.mkdir()

        remote = make_local_remote(str(dest_dir))
        mgr = make_manager()
        result = mgr.upload_to_local(remote, src_dir, str(dest_dir))

        assert result is True
        assert (dest_dir / "backup_20260101").exists()
        assert (dest_dir / "backup_20260101" / "containers.tar.gz").exists()
        assert (dest_dir / "backup_20260101" / "volumes" / "data.tar.gz").exists()

    def test_creates_dest_dir_if_missing(self, tmp_path):
        src_file = tmp_path / "file.txt"
        src_file.write_bytes(b"data")
        dest_dir = tmp_path / "new_remote" / "subdir"
        # dest_dir does NOT exist yet

        remote = make_local_remote(str(dest_dir))
        mgr = make_manager()
        result = mgr.upload_to_local(remote, src_file, str(dest_dir))

        assert result is True
        assert dest_dir.exists()

    def test_overwrites_existing_directory(self, tmp_path):
        src_dir = tmp_path / "bkp"
        src_dir.mkdir()
        (src_dir / "new.txt").write_bytes(b"new")
        dest_dir = tmp_path / "remote"
        dest_dir.mkdir()
        existing = dest_dir / "bkp"
        existing.mkdir()
        (existing / "old.txt").write_bytes(b"old")

        remote = make_local_remote(str(dest_dir))
        mgr = make_manager()
        mgr.upload_to_local(remote, src_dir, str(dest_dir))

        assert (dest_dir / "bkp" / "new.txt").exists()


# ---------------------------------------------------------------------------
# _list_local_backups
# ---------------------------------------------------------------------------

class TestListLocalBackups:
    def test_lists_directories(self, tmp_path):
        (tmp_path / "backup_20260101").mkdir()
        (tmp_path / "backup_20260102").mkdir()
        (tmp_path / "some_file.txt").write_bytes(b"not a dir")

        remote = make_local_remote(str(tmp_path))
        mgr = make_manager()
        backups = mgr._list_local_backups(remote)

        assert "backup_20260101" in backups
        assert "backup_20260102" in backups
        assert "some_file.txt" not in backups

    def test_empty_dir_returns_empty_list(self, tmp_path):
        remote = make_local_remote(str(tmp_path))
        mgr = make_manager()
        assert mgr._list_local_backups(remote) == []

    def test_nonexistent_path_returns_empty_list(self):
        remote = make_local_remote("/tmp/definitely_does_not_exist_abc123")
        mgr = make_manager()
        assert mgr._list_local_backups(remote) == []


# ---------------------------------------------------------------------------
# list_backups dispatch
# ---------------------------------------------------------------------------

class TestListBackupsDispatch:
    def test_local_remote_calls_list_local(self, tmp_path, monkeypatch):
        remote = make_local_remote(str(tmp_path))
        mgr = make_manager()
        called = []
        monkeypatch.setattr(mgr, "_list_local_backups", lambda r: called.append(r) or ["b1"])
        result = mgr.list_backups(remote)
        assert called and result == ["b1"]

    def test_sftp_remote_returns_empty(self):
        remote = RemoteStorage(name="sftp", type="sftp", path="/backups")
        mgr = make_manager()
        result = mgr.list_backups(remote)
        assert result == []


# ---------------------------------------------------------------------------
# upload_backup dispatch
# ---------------------------------------------------------------------------

class TestUploadBackupDispatch:
    def test_local_type_calls_upload_to_local(self, tmp_path, monkeypatch):
        remote = make_local_remote(str(tmp_path))
        mgr = make_manager()
        called = []
        monkeypatch.setattr(mgr, "upload_to_local", lambda r, lp, rp: called.append(True) or True)
        result = mgr.upload_backup(remote, tmp_path, "backup_20260101")
        assert result is True
        assert called

    def test_unknown_type_returns_false(self):
        remote = RemoteStorage(name="mystery", type="nfs", path="/backups")
        mgr = make_manager()
        result = mgr.upload_backup(remote, Path("/tmp"), "backup_name")
        assert result is False

    def test_rclone_type_checks_binary(self, monkeypatch):
        remote = RemoteStorage(name="gdrive", type="rclone", remote_name="gdrive", path="/bkps")
        mgr = make_manager()
        monkeypatch.setattr("shutil.which", lambda _: None)  # rclone not installed
        result = mgr.upload_to_rclone(remote, Path("/tmp"), "bkps/backup_20260101")
        assert result is False

    def test_rclone_without_remote_name_returns_false(self):
        remote = RemoteStorage(name="r", type="rclone", path="/bkps")  # no remote_name
        mgr = make_manager()
        result = mgr.upload_to_rclone(remote, Path("/tmp"), "bkps/b")
        assert result is False

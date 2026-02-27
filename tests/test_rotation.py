"""
tests/test_rotation.py
Tests for bbackup.rotation: BackupRotation age categorization,
retention filtering, storage quota, local storage calculation.
"""

import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from bbackup.config import RemoteStorage, RetentionPolicy
from bbackup.rotation import BackupRotation


def make_rotation(daily=7, weekly=4, monthly=12, max_gb=0) -> BackupRotation:
    policy = RetentionPolicy(daily=daily, weekly=weekly, monthly=monthly, max_storage_gb=max_gb)
    return BackupRotation(retention=policy)


# ---------------------------------------------------------------------------
# Age categorization
# ---------------------------------------------------------------------------

class TestAgeCategorization:
    def test_today_is_daily(self):
        r = make_rotation()
        assert r.get_backup_age_category(datetime.now()) == "daily"

    def test_yesterday_is_daily(self):
        r = make_rotation()
        assert r.get_backup_age_category(datetime.now() - timedelta(days=1)) == "daily"

    def test_six_days_ago_is_daily(self):
        r = make_rotation()
        assert r.get_backup_age_category(datetime.now() - timedelta(days=6)) == "daily"

    def test_seven_days_ago_is_weekly(self):
        r = make_rotation()
        assert r.get_backup_age_category(datetime.now() - timedelta(days=7)) == "weekly"

    def test_twenty_days_ago_is_weekly(self):
        r = make_rotation()
        assert r.get_backup_age_category(datetime.now() - timedelta(days=20)) == "weekly"

    def test_thirty_days_ago_is_monthly(self):
        r = make_rotation()
        assert r.get_backup_age_category(datetime.now() - timedelta(days=30)) == "monthly"

    def test_ninety_days_ago_is_monthly(self):
        r = make_rotation()
        assert r.get_backup_age_category(datetime.now() - timedelta(days=90)) == "monthly"


# ---------------------------------------------------------------------------
# should_keep_backup
# ---------------------------------------------------------------------------

class TestShouldKeepBackup:
    def test_keeps_recent_backup(self):
        r = make_rotation()
        assert r.should_keep_backup(datetime.now()) is True

    def test_keeps_sunday_weekly(self):
        r = make_rotation()
        # Find the most recent Sunday that is 7-29 days ago (weekly category)
        base = datetime.now() - timedelta(days=10)
        days_since_sunday = base.weekday() + 1  # weekday() 0=Mon, 6=Sun -> Sunday is 6
        sunday = base - timedelta(days=(base.weekday() + 1) % 7)
        if 7 <= (datetime.now() - sunday).days < 30:
            assert r.should_keep_backup(sunday) is True

    def test_keeps_first_of_month_monthly(self):
        r = make_rotation()
        first = datetime(2025, 1, 1)  # old enough to be monthly
        # Only check if the date is old enough to be monthly category
        if r.get_backup_age_category(first) == "monthly":
            assert r.should_keep_backup(first) is True


# ---------------------------------------------------------------------------
# _parse_backup_date
# ---------------------------------------------------------------------------

class TestParseBackupDate:
    def test_parses_standard_format(self):
        r = make_rotation()
        d = r._parse_backup_date("backup_20250115_143000")
        assert d is not None
        assert d.year == 2025
        assert d.month == 1
        assert d.day == 15

    def test_parses_name_with_extra_parts(self):
        r = make_rotation()
        d = r._parse_backup_date("myrepo_backup_20241201_000000")
        assert d is not None
        assert d.year == 2024
        assert d.month == 12
        assert d.day == 1

    def test_returns_none_for_unparseable(self):
        r = make_rotation()
        assert r._parse_backup_date("backup_no_date_here") is None

    def test_returns_none_for_empty_string(self):
        r = make_rotation()
        assert r._parse_backup_date("") is None

    def test_returns_none_for_invalid_date(self):
        r = make_rotation()
        assert r._parse_backup_date("backup_20251399_000000") is None  # month 13 invalid


# ---------------------------------------------------------------------------
# filter_backups_by_retention
# ---------------------------------------------------------------------------

class TestFilterBackupsByRetention:
    def _make_backup_names(self, dates):
        return [f"backup_{d.strftime('%Y%m%d')}_120000" for d in dates]

    def test_keeps_up_to_daily_limit(self):
        r = make_rotation(daily=3, weekly=2, monthly=2)
        # 5 backups within the last 6 days
        dates = [datetime.now() - timedelta(days=i) for i in range(5)]
        names = self._make_backup_names(dates)
        keep, delete = r.filter_backups_by_retention(names, Path("/tmp/test"))
        assert len(keep) <= 3

    def test_deletes_excess_daily(self):
        r = make_rotation(daily=2, weekly=0, monthly=0)
        dates = [datetime.now() - timedelta(days=i) for i in range(5)]
        names = self._make_backup_names(dates)
        keep, delete = r.filter_backups_by_retention(names, Path("/tmp/test"))
        assert len(delete) >= 1

    def test_keep_plus_delete_equals_total(self):
        r = make_rotation(daily=3, weekly=2, monthly=2)
        dates = [datetime.now() - timedelta(days=i * 3) for i in range(10)]
        names = self._make_backup_names(dates)
        keep, delete = r.filter_backups_by_retention(names, Path("/tmp/test"))
        assert len(keep) + len(delete) == len(names)

    def test_empty_backups_returns_empty(self):
        r = make_rotation()
        keep, delete = r.filter_backups_by_retention([], Path("/tmp/test"))
        assert keep == []
        assert delete == []

    def test_unparseable_names_excluded(self):
        r = make_rotation(daily=5)
        names = ["backup_no_date", "also_no_date"]
        keep, delete = r.filter_backups_by_retention(names, Path("/tmp/test"))
        assert keep == []
        assert delete == []


# ---------------------------------------------------------------------------
# check_storage_quota
# ---------------------------------------------------------------------------

class TestStorageQuota:
    def test_quota_disabled_when_max_zero(self):
        r = make_rotation(max_gb=0)
        remote = RemoteStorage(name="r", type="local", path="/tmp")
        result = r.check_storage_quota(remote, Path("/tmp"))
        assert result["enabled"] is False
        assert result["cleanup_needed"] is False

    def test_quota_enabled_when_max_set(self, tmp_path):
        r = make_rotation(max_gb=1)
        remote = RemoteStorage(name="r", type="local", path=str(tmp_path))
        result = r.check_storage_quota(remote, tmp_path)
        assert result["enabled"] is True
        assert result["used_gb"] >= 0
        assert result["max_gb"] == 1

    def test_no_warning_when_usage_low(self, tmp_path):
        r = make_rotation(max_gb=1000)
        remote = RemoteStorage(name="r", type="local", path=str(tmp_path))
        result = r.check_storage_quota(remote, tmp_path)
        assert result["warning"] is False
        assert result["cleanup_needed"] is False


# ---------------------------------------------------------------------------
# _calculate_local_storage
# ---------------------------------------------------------------------------

class TestLocalStorageCalculation:
    def test_empty_dir_returns_zero(self, tmp_path):
        r = make_rotation()
        assert r._calculate_local_storage(tmp_path) == 0

    def test_counts_file_sizes(self, tmp_path):
        (tmp_path / "file1.txt").write_bytes(b"A" * 100)
        (tmp_path / "file2.txt").write_bytes(b"B" * 200)
        r = make_rotation()
        total = r._calculate_local_storage(tmp_path)
        assert total == 300

    def test_counts_nested_files(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "nested.txt").write_bytes(b"X" * 500)
        r = make_rotation()
        assert r._calculate_local_storage(tmp_path) == 500

    def test_nonexistent_path_returns_zero(self):
        r = make_rotation()
        assert r._calculate_local_storage(Path("/tmp/definitely_does_not_exist_12345")) == 0

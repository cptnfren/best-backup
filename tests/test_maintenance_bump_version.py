"""
tests/test_maintenance_bump_version.py
Tests for maintenance/bump_version.py: semver parsing, bump logic,
commit classification, CHANGELOG generation, version sync.
"""

import sys
import re
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "maintenance"))

import bump_version  # noqa: E402


# ---------------------------------------------------------------------------
# parse_semver
# ---------------------------------------------------------------------------

class TestParseSemver:
    def test_parses_basic(self):
        assert bump_version.parse_semver("1.2.3") == (1, 2, 3)

    def test_parses_zeros(self):
        assert bump_version.parse_semver("0.0.0") == (0, 0, 0)

    def test_parses_large_numbers(self):
        assert bump_version.parse_semver("10.20.30") == (10, 20, 30)

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            bump_version.parse_semver("1.2")

    def test_non_numeric_raises(self):
        with pytest.raises((ValueError, TypeError)):
            bump_version.parse_semver("a.b.c")


# ---------------------------------------------------------------------------
# bump
# ---------------------------------------------------------------------------

class TestBump:
    def test_patch_bump(self):
        assert bump_version.bump(1, 2, 3, "patch") == "1.2.4"

    def test_minor_bump_resets_patch(self):
        assert bump_version.bump(1, 2, 3, "minor") == "1.3.0"

    def test_major_bump_resets_minor_and_patch(self):
        assert bump_version.bump(1, 2, 3, "major") == "2.0.0"

    def test_patch_on_zero(self):
        assert bump_version.bump(0, 0, 0, "patch") == "0.0.1"

    def test_minor_on_zero(self):
        assert bump_version.bump(0, 0, 0, "minor") == "0.1.0"

    def test_major_on_zero(self):
        assert bump_version.bump(0, 0, 0, "major") == "1.0.0"


# ---------------------------------------------------------------------------
# determine_bump_type
# ---------------------------------------------------------------------------

class TestDetermineBumpType:
    def test_feat_gives_minor(self):
        assert bump_version.determine_bump_type(["feat: add new feature"]) == "minor"

    def test_feat_with_scope_gives_minor(self):
        assert bump_version.determine_bump_type(["feat(api): new endpoint"]) == "minor"

    def test_fix_gives_patch(self):
        assert bump_version.determine_bump_type(["fix: resolve crash"]) == "patch"

    def test_docs_gives_patch(self):
        assert bump_version.determine_bump_type(["docs: update README"]) == "patch"

    def test_chore_gives_patch(self):
        assert bump_version.determine_bump_type(["chore: bump deps"]) == "patch"

    def test_breaking_change_in_body_gives_major(self):
        msgs = ["feat: new api", "BREAKING CHANGE: old api removed"]
        assert bump_version.determine_bump_type(msgs) == "major"

    def test_exclamation_prefix_gives_major(self):
        assert bump_version.determine_bump_type(["feat!: redesign everything"]) == "major"

    def test_mixed_feat_and_fix_gives_minor(self):
        msgs = ["fix: minor fix", "feat: new feature"]
        assert bump_version.determine_bump_type(msgs) == "minor"

    def test_empty_messages_gives_patch(self):
        assert bump_version.determine_bump_type([]) == "patch"

    def test_unrecognized_prefix_gives_patch(self):
        assert bump_version.determine_bump_type(["wip: random stuff"]) == "patch"


# ---------------------------------------------------------------------------
# read_version / write_version
# ---------------------------------------------------------------------------

class TestReadWriteVersion:
    def test_read_version(self, tmp_path):
        (tmp_path / "VERSION").write_text("2.3.4\n")
        original_file = bump_version.VERSION_FILE
        bump_version.VERSION_FILE = tmp_path / "VERSION"
        try:
            assert bump_version.read_version() == "2.3.4"
        finally:
            bump_version.VERSION_FILE = original_file

    def test_write_version(self, tmp_path):
        ver_file = tmp_path / "VERSION"
        original_file = bump_version.VERSION_FILE
        bump_version.VERSION_FILE = ver_file
        try:
            bump_version.write_version("3.0.0")
            assert ver_file.read_text() == "3.0.0\n"
        finally:
            bump_version.VERSION_FILE = original_file

    def test_write_then_read(self, tmp_path):
        ver_file = tmp_path / "VERSION"
        original_file = bump_version.VERSION_FILE
        bump_version.VERSION_FILE = ver_file
        try:
            bump_version.write_version("5.6.7")
            assert bump_version.read_version() == "5.6.7"
        finally:
            bump_version.VERSION_FILE = original_file


# ---------------------------------------------------------------------------
# sync_version_in_file
# ---------------------------------------------------------------------------

class TestSyncVersionInFile:
    def _call(self, f, pattern, replace, version, tmp_path):
        """Call sync_version_in_file with REPO_ROOT patched to tmp_path."""
        original = bump_version.REPO_ROOT
        bump_version.REPO_ROOT = tmp_path
        try:
            return bump_version.sync_version_in_file(f, pattern, replace, version)
        finally:
            bump_version.REPO_ROOT = original

    def test_updates_python_init(self, tmp_path):
        f = tmp_path / "__init__.py"
        f.write_text('__version__ = "1.0.0"\n')
        result = self._call(
            f, r'(__version__\s*=\s*")[^"]+(")', r'\g<1>{version}\g<2>', "2.0.0", tmp_path
        )
        assert result is True
        assert '2.0.0' in f.read_text()

    def test_already_current_returns_false(self, tmp_path):
        f = tmp_path / "__init__.py"
        f.write_text('__version__ = "2.0.0"\n')
        result = self._call(
            f, r'(__version__\s*=\s*")[^"]+(")', r'\g<1>{version}\g<2>', "2.0.0", tmp_path
        )
        assert result is False

    def test_no_match_returns_false(self, tmp_path):
        f = tmp_path / "file.py"
        f.write_text("version_string = 'old'\n")
        result = self._call(
            f, r'(__version__\s*=\s*")[^"]+(")', r'\g<1>{version}\g<2>', "9.9.9", tmp_path
        )
        assert result is False

    def test_missing_file_returns_false(self, tmp_path):
        missing = tmp_path / "missing.py"
        result = self._call(
            missing, r'(__version__\s*=\s*")[^"]+(")', r'\g<1>{version}\g<2>', "1.0.0", tmp_path
        )
        assert result is False

    def test_updates_package_json_style(self, tmp_path):
        f = tmp_path / "package.json"
        f.write_text('{\n  "version": "0.9.0"\n}\n')
        result = self._call(
            f, r'("version":\s*")[^"]+(")', r'\g<1>{version}\g<2>', "1.0.0", tmp_path
        )
        assert result is True
        assert '"version": "1.0.0"' in f.read_text()


# ---------------------------------------------------------------------------
# generate_changelog_entry
# ---------------------------------------------------------------------------

class TestGenerateChangelogEntry:
    def test_includes_version_header(self):
        entry = bump_version.generate_changelog_entry("2.0.0", ["feat: add something"])
        assert "## [2.0.0]" in entry

    def test_includes_today_date(self):
        from datetime import date
        today = date.today().isoformat()
        entry = bump_version.generate_changelog_entry("1.0.0", ["feat: new thing"])
        assert today in entry

    def test_feat_appears_in_added_section(self):
        entry = bump_version.generate_changelog_entry("1.0.0", ["feat: add widget"])
        assert "### Added" in entry
        assert "Add widget" in entry

    def test_fix_appears_in_fixed_section(self):
        entry = bump_version.generate_changelog_entry("1.0.0", ["fix: resolve crash"])
        assert "### Fixed" in entry
        assert "Resolve crash" in entry

    def test_docs_appears_in_documentation_section(self):
        entry = bump_version.generate_changelog_entry("1.0.0", ["docs: update readme"])
        assert "### Documentation" in entry

    def test_chore_appears_in_maintenance_section(self):
        entry = bump_version.generate_changelog_entry("1.0.0", ["chore: update deps"])
        assert "### Maintenance" in entry

    def test_version_bump_commit_excluded(self):
        entry = bump_version.generate_changelog_entry(
            "1.0.0", ["chore: bump version to 0.9.0", "feat: real feature"]
        )
        assert "bump version to 0.9.0" not in entry
        assert "Real feature" in entry

    def test_empty_messages_gives_fallback(self):
        entry = bump_version.generate_changelog_entry("1.0.0", [])
        assert "## [1.0.0]" in entry

    def test_subject_capitalized(self):
        entry = bump_version.generate_changelog_entry("1.0.0", ["feat: lowercase subject"])
        assert "Lowercase subject" in entry


# ---------------------------------------------------------------------------
# prepend_changelog
# ---------------------------------------------------------------------------

class TestPrependChangelog:
    def _seed_changelog(self, tmp_path):
        content = textwrap.dedent("""\
            # Changelog

            ## [Unreleased]

            ---

            ## [1.0.0] - 2026-01-01

            ### Added
            - Initial release

            ---

            [Unreleased]: https://github.com/owner/repo/compare/v1.0.0...HEAD
            [1.0.0]: https://github.com/owner/repo/releases/tag/v1.0.0
        """)
        f = tmp_path / "CHANGELOG.md"
        f.write_text(content)
        return f

    def test_prepends_new_section(self, tmp_path):
        changelog = self._seed_changelog(tmp_path)
        original_file = bump_version.CHANGELOG_FILE
        bump_version.CHANGELOG_FILE = changelog
        try:
            entry = "## [1.1.0] - 2026-02-01\n\n### Added\n\n- New feature\n\n"
            bump_version.prepend_changelog("1.1.0", entry)
            content = changelog.read_text()
            assert "## [1.1.0]" in content
            assert "## [1.0.0]" in content
        finally:
            bump_version.CHANGELOG_FILE = original_file

    def test_dry_run_does_not_modify(self, tmp_path):
        changelog = self._seed_changelog(tmp_path)
        original_content = changelog.read_text()
        original_file = bump_version.CHANGELOG_FILE
        bump_version.CHANGELOG_FILE = changelog
        try:
            entry = "## [9.9.9] - 2099-01-01\n\n### Added\n\n- Something\n\n"
            bump_version.prepend_changelog("9.9.9", entry, dry_run=True)
            assert changelog.read_text() == original_content
        finally:
            bump_version.CHANGELOG_FILE = original_file

    def test_missing_changelog_skips_gracefully(self, tmp_path):
        original_file = bump_version.CHANGELOG_FILE
        bump_version.CHANGELOG_FILE = tmp_path / "CHANGELOG.md"  # does not exist
        try:
            bump_version.prepend_changelog("1.0.0", "## [1.0.0]\n", dry_run=False)
            # Should not raise
        finally:
            bump_version.CHANGELOG_FILE = original_file

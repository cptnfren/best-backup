"""
tests/test_maintenance_stamp.py
Tests for maintenance/stamp.py: footer stamping, idempotency,
sentinel replacement, code file sync, missing file handling.
"""

import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "maintenance"))

import stamp  # noqa: E402


FOOTER_START = stamp.FOOTER_START
FOOTER_END = stamp.FOOTER_END


def write_project_yaml(tmp_path, overrides=None) -> dict:
    cfg = {
        "project": {
            "name": "test-proj",
            "description": "Test",
            "repository": "https://github.com/owner/test-proj",
        },
        "author": {"name": "Jane Dev", "github": "janedev", "email": ""},
        "company": {"name": "Dev Corp", "url": "https://devcorp.example.com/"},
        "copyright": {"year": 2026, "license": "MIT"},
        "stamp_targets": [],
        "version_sync": {"code_files": []},
        "doc_map": [],
        "public_docs": [],
    }
    if overrides:
        for k, v in overrides.items():
            cfg[k] = v
    path = tmp_path / "project.yaml"
    path.write_text(yaml.dump(cfg))
    return cfg


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------

class TestLoadConfig:
    def test_loads_valid_config(self, tmp_path):
        write_project_yaml(tmp_path)
        original = stamp.PROJECT_YAML
        stamp.PROJECT_YAML = tmp_path / "project.yaml"
        try:
            cfg = stamp.load_config()
            assert cfg["author"]["name"] == "Jane Dev"
        finally:
            stamp.PROJECT_YAML = original

    def test_missing_config_raises(self, tmp_path):
        original = stamp.PROJECT_YAML
        stamp.PROJECT_YAML = tmp_path / "does_not_exist.yaml"
        try:
            with pytest.raises(SystemExit):
                stamp.load_config()
        finally:
            stamp.PROJECT_YAML = original

    def test_load_config_custom_path(self, tmp_path):
        write_project_yaml(tmp_path)
        # Patch PROJECT_YAML directly
        original = stamp.PROJECT_YAML
        stamp.PROJECT_YAML = tmp_path / "project.yaml"
        try:
            cfg = stamp.load_config()
            assert cfg["company"]["name"] == "Dev Corp"
        finally:
            stamp.PROJECT_YAML = original


# ---------------------------------------------------------------------------
# build_footer
# ---------------------------------------------------------------------------

class TestBuildFooter:
    def _cfg(self):
        return {
            "author": {"name": "Alice Smith"},
            "company": {"name": "Acme Ltd", "url": "https://acme.example.com/"},
            "copyright": {"year": 2026, "license": "Apache-2.0"},
            "project": {"repository": "https://github.com/acme/myrepo"},
        }

    def test_footer_contains_author(self):
        footer = stamp.build_footer(self._cfg())
        assert "Alice Smith" in footer

    def test_footer_contains_company_name(self):
        footer = stamp.build_footer(self._cfg())
        assert "Acme Ltd" in footer

    def test_footer_contains_company_url(self):
        footer = stamp.build_footer(self._cfg())
        assert "https://acme.example.com/" in footer

    def test_footer_contains_year(self):
        footer = stamp.build_footer(self._cfg())
        assert "2026" in footer

    def test_footer_contains_license(self):
        footer = stamp.build_footer(self._cfg())
        assert "Apache-2.0" in footer

    def test_footer_contains_sentinels(self):
        footer = stamp.build_footer(self._cfg())
        assert FOOTER_START in footer
        assert FOOTER_END in footer

    def test_footer_is_centered_html(self):
        footer = stamp.build_footer(self._cfg())
        assert 'align="center"' in footer

    def test_footer_license_links_to_repo(self):
        footer = stamp.build_footer(self._cfg())
        assert "https://github.com/acme/myrepo/blob/main/LICENSE" in footer


# ---------------------------------------------------------------------------
# stamp_file
# ---------------------------------------------------------------------------

class TestStampFile:
    def _cfg(self):
        return {
            "author": {"name": "Bob Dev"},
            "company": {"name": "Corp", "url": "https://corp.example.com/"},
            "copyright": {"year": 2026, "license": "MIT"},
            "project": {"repository": "https://github.com/corp/repo"},
        }

    def test_stamps_new_file(self, tmp_path):
        doc = tmp_path / "README.md"
        doc.write_text("# My Project\n\nSome content.\n")
        footer = stamp.build_footer(self._cfg())
        result = stamp.stamp_file(doc, footer, dry_run=False)
        assert result in ("stamped", "updated")
        content = doc.read_text()
        assert FOOTER_START in content
        assert FOOTER_END in content

    def test_idempotent_second_stamp(self, tmp_path):
        doc = tmp_path / "README.md"
        doc.write_text("# Project\n")
        footer = stamp.build_footer(self._cfg())
        stamp.stamp_file(doc, footer, dry_run=False)
        result2 = stamp.stamp_file(doc, footer, dry_run=False)
        assert result2 == "unchanged"

    def test_single_sentinel_block_after_two_stamps(self, tmp_path):
        doc = tmp_path / "README.md"
        doc.write_text("# Content\n")
        footer = stamp.build_footer(self._cfg())
        stamp.stamp_file(doc, footer, dry_run=False)
        stamp.stamp_file(doc, footer, dry_run=False)
        content = doc.read_text()
        assert content.count(FOOTER_START) == 1
        assert content.count(FOOTER_END) == 1

    def test_dry_run_does_not_write(self, tmp_path):
        doc = tmp_path / "README.md"
        original = "# No changes please\n"
        doc.write_text(original)
        footer = stamp.build_footer(self._cfg())
        stamp.stamp_file(doc, footer, dry_run=True)
        assert doc.read_text() == original

    def test_missing_file_returns_skipped(self, tmp_path):
        missing = tmp_path / "DOES_NOT_EXIST.md"
        footer = stamp.build_footer(self._cfg())
        result = stamp.stamp_file(missing, footer, dry_run=False)
        assert result == "skipped"

    def test_replaces_outdated_footer(self, tmp_path):
        doc = tmp_path / "README.md"
        old_footer = f"{FOOTER_START}\n<p>Old footer</p>\n{FOOTER_END}"
        doc.write_text(f"# Title\n\n{old_footer}\n")
        footer = stamp.build_footer(self._cfg())
        result = stamp.stamp_file(doc, footer, dry_run=False)
        assert result == "updated"
        assert "Old footer" not in doc.read_text()
        assert "Bob Dev" in doc.read_text()

    def test_content_before_footer_preserved(self, tmp_path):
        doc = tmp_path / "README.md"
        doc.write_text("# Title\n\nImportant content.\n")
        footer = stamp.build_footer(self._cfg())
        stamp.stamp_file(doc, footer, dry_run=False)
        content = doc.read_text()
        assert "Important content." in content


# ---------------------------------------------------------------------------
# sync_code_files
# ---------------------------------------------------------------------------

class TestSyncCodeFiles:
    def _base_cfg(self, tmp_path):
        return {
            "author": {"name": "Test Author", "email": ""},
            "company": {"name": "Test Corp"},
            "copyright": {"year": 2025, "license": "MIT"},
            "project": {"repository": "https://github.com/x/y"},
            "version_sync": {"code_files": []},
        }

    def test_updates_license_copyright(self, tmp_path):
        lic = tmp_path / "LICENSE"
        lic.write_text("MIT License\n\nCopyright (c) 2020 Old Author\n\nPermission...\n")
        # Patch REPO_ROOT for the test
        original_root = stamp.REPO_ROOT
        stamp.REPO_ROOT = tmp_path
        try:
            cfg = self._base_cfg(tmp_path)
            results = stamp.sync_code_files(cfg, dry_run=False)
            status_map = dict(results)
            assert status_map.get("LICENSE (copyright)") == "updated"
            assert "Test Author" in lic.read_text()
            assert "Test Corp" in lic.read_text()
        finally:
            stamp.REPO_ROOT = original_root

    def test_dry_run_skips_license_write(self, tmp_path):
        lic = tmp_path / "LICENSE"
        original = "MIT License\n\nCopyright (c) 2020 Old Name\n"
        lic.write_text(original)
        original_root = stamp.REPO_ROOT
        stamp.REPO_ROOT = tmp_path
        try:
            cfg = self._base_cfg(tmp_path)
            stamp.sync_code_files(cfg, dry_run=True)
            assert lic.read_text() == original
        finally:
            stamp.REPO_ROOT = original_root

    def test_missing_license_returns_skipped(self, tmp_path):
        original_root = stamp.REPO_ROOT
        stamp.REPO_ROOT = tmp_path  # no LICENSE file here
        try:
            cfg = self._base_cfg(tmp_path)
            results = stamp.sync_code_files(cfg, dry_run=False)
            status_map = dict(results)
            assert status_map.get("LICENSE (copyright)") == "skipped"
        finally:
            stamp.REPO_ROOT = original_root


# ---------------------------------------------------------------------------
# stamp_docs end-to-end
# ---------------------------------------------------------------------------

class TestStampDocs:
    def _cfg(self, tmp_path, targets):
        return {
            "author": {"name": "End User"},
            "company": {"name": "End Corp", "url": "https://end.example.com/"},
            "copyright": {"year": 2026, "license": "MIT"},
            "project": {"repository": "https://github.com/end/proj"},
            "stamp_targets": [str(t) for t in targets],
        }

    def test_stamps_multiple_files(self, tmp_path):
        docs = []
        for name in ["README.md", "CHANGELOG.md", "INSTALL.md"]:
            p = tmp_path / name
            p.write_text(f"# {name}\n\nContent.\n")
            docs.append(p)

        cfg = self._cfg(tmp_path, docs)
        original_root = stamp.REPO_ROOT
        stamp.REPO_ROOT = tmp_path
        try:
            results = stamp.stamp_docs(cfg, dry_run=False)
            statuses = [r[1] for r in results]
            assert all(s == "stamped" for s in statuses)
        finally:
            stamp.REPO_ROOT = original_root

    def test_skips_missing_target(self, tmp_path):
        missing = tmp_path / "MISSING.md"
        cfg = self._cfg(tmp_path, [missing])
        original_root = stamp.REPO_ROOT
        stamp.REPO_ROOT = tmp_path
        try:
            results = stamp.stamp_docs(cfg, dry_run=False)
            assert results[0][1] == "skipped"
        finally:
            stamp.REPO_ROOT = original_root

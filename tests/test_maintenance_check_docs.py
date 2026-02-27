"""
tests/test_maintenance_check_docs.py
Tests for maintenance/check_docs.py: broken link detection,
doc staleness mapping, DocCheckResult, glob matching.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "maintenance"))

import check_docs  # noqa: E402
from check_docs import DocCheckResult, check_internal_links, match_glob  # noqa: E402


# ---------------------------------------------------------------------------
# match_glob
# ---------------------------------------------------------------------------

class TestMatchGlob:
    def test_exact_match(self):
        assert match_glob("bbackup/cli.py", ["bbackup/cli.py"]) is True

    def test_wildcard_match(self):
        assert match_glob("bbackup/cli.py", ["bbackup/*.py"]) is True

    def test_recursive_wildcard(self):
        assert match_glob("bbackup/management/health.py", ["bbackup/management/*.py"]) is True

    def test_no_match(self):
        assert match_glob("README.md", ["bbackup/*.py"]) is False

    def test_multiple_patterns_first_matches(self):
        assert match_glob("bbackup/cli.py", ["setup.py", "bbackup/cli.py"]) is True

    def test_empty_pattern_list(self):
        assert match_glob("anything.py", []) is False


# ---------------------------------------------------------------------------
# check_internal_links
# ---------------------------------------------------------------------------

class TestCheckInternalLinks:
    def test_no_links_returns_empty(self, tmp_path):
        doc = tmp_path / "README.md"
        doc.write_text("# Title\n\nNo links here.\n")
        assert check_internal_links(doc) == []

    def test_valid_link_not_flagged(self, tmp_path):
        target = tmp_path / "docs" / "guide.md"
        target.parent.mkdir()
        target.write_text("# Guide\n")
        doc = tmp_path / "README.md"
        doc.write_text("[Guide](docs/guide.md)\n")
        broken = check_internal_links(doc)
        assert broken == []

    def test_broken_relative_link_detected(self, tmp_path):
        doc = tmp_path / "README.md"
        doc.write_text("[Missing](docs/missing.md)\n")
        broken = check_internal_links(doc)
        assert "docs/missing.md" in broken

    def test_http_links_skipped(self, tmp_path):
        doc = tmp_path / "README.md"
        doc.write_text("[GitHub](https://github.com/owner/repo)\n")
        assert check_internal_links(doc) == []

    def test_anchor_links_skipped(self, tmp_path):
        doc = tmp_path / "README.md"
        doc.write_text("[Section](#section-header)\n")
        assert check_internal_links(doc) == []

    def test_mixed_links(self, tmp_path):
        existing = tmp_path / "INSTALL.md"
        existing.write_text("# Install\n")
        doc = tmp_path / "README.md"
        doc.write_text(
            "[Valid](INSTALL.md)\n"
            "[Broken](MISSING.md)\n"
            "[Web](https://example.com)\n"
            "[Anchor](#top)\n"
        )
        broken = check_internal_links(doc)
        assert "MISSING.md" in broken
        assert "INSTALL.md" not in broken
        assert "https://example.com" not in broken

    def test_link_with_anchor_fragment(self, tmp_path):
        target = tmp_path / "docs.md"
        target.write_text("# Docs\n")
        doc = tmp_path / "README.md"
        doc.write_text("[Docs Section](docs.md#section)\n")
        broken = check_internal_links(doc)
        assert broken == []

    def test_missing_file_returns_empty(self, tmp_path):
        missing_doc = tmp_path / "MISSING.md"
        assert check_internal_links(missing_doc) == []


# ---------------------------------------------------------------------------
# DocCheckResult
# ---------------------------------------------------------------------------

class TestDocCheckResult:
    def test_default_is_ok(self):
        r = DocCheckResult()
        assert r.ok is True
        assert r.changed_sources == []
        assert r.docs_to_review == []
        assert r.broken_links == []

    def test_can_hold_broken_links(self):
        r = DocCheckResult(broken_links=[("README.md", "missing.md")], ok=False)
        assert r.ok is False
        assert r.broken_links == [("README.md", "missing.md")]

    def test_can_hold_docs_to_review(self):
        r = DocCheckResult(docs_to_review=[("README.md", "CLI changed")], ok=False)
        assert r.ok is False
        assert r.docs_to_review == [("README.md", "CLI changed")]


# ---------------------------------------------------------------------------
# run() - patched git
# ---------------------------------------------------------------------------

class TestRunFunction:
    def _make_docs(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text("# Test Project\n\nNo internal links.\n")
        return readme

    def test_run_no_changed_files_is_ok(self, tmp_path):
        self._make_docs(tmp_path)
        original_root = check_docs.REPO_ROOT
        check_docs.REPO_ROOT = tmp_path
        try:
            with patch("check_docs.get_changed_files", return_value=[]):
                result = check_docs.run(since="HEAD~1")
            assert result.ok is True
            assert result.docs_to_review == []
        finally:
            check_docs.REPO_ROOT = original_root

    def test_run_detects_broken_link(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text("[Missing](DOES_NOT_EXIST.md)\n")
        original_root = check_docs.REPO_ROOT
        original_public = check_docs.PUBLIC_DOCS
        check_docs.REPO_ROOT = tmp_path
        check_docs.PUBLIC_DOCS = ["README.md"]
        try:
            with patch("check_docs.get_changed_files", return_value=[]):
                result = check_docs.run(since="HEAD~1")
            assert result.ok is False
            assert any("DOES_NOT_EXIST.md" in link for _, link in result.broken_links)
        finally:
            check_docs.REPO_ROOT = original_root
            check_docs.PUBLIC_DOCS = original_public

    def test_run_flags_stale_docs(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text("# Project\n")
        original_root = check_docs.REPO_ROOT
        original_map = check_docs.SOURCE_TO_DOC_MAP
        original_public = check_docs.PUBLIC_DOCS
        check_docs.REPO_ROOT = tmp_path
        check_docs.SOURCE_TO_DOC_MAP = [
            (["bbackup/cli.py"], ["README.md"], "CLI changed"),
        ]
        check_docs.PUBLIC_DOCS = ["README.md"]
        try:
            with patch("check_docs.get_changed_files", return_value=["bbackup/cli.py"]):
                result = check_docs.run(since="HEAD~1")
            assert any("README.md" in doc for doc, _ in result.docs_to_review)
        finally:
            check_docs.REPO_ROOT = original_root
            check_docs.SOURCE_TO_DOC_MAP = original_map
            check_docs.PUBLIC_DOCS = original_public

    def test_run_all_clean_returns_ok(self, tmp_path):
        readme = tmp_path / "README.md"
        existing = tmp_path / "INSTALL.md"
        existing.write_text("# Install\n")
        readme.write_text("[Install](INSTALL.md)\n")
        original_root = check_docs.REPO_ROOT
        original_public = check_docs.PUBLIC_DOCS
        check_docs.REPO_ROOT = tmp_path
        check_docs.PUBLIC_DOCS = ["README.md"]
        try:
            with patch("check_docs.get_changed_files", return_value=[]):
                result = check_docs.run(since="HEAD~1")
            assert result.ok is True
        finally:
            check_docs.REPO_ROOT = original_root
            check_docs.PUBLIC_DOCS = original_public

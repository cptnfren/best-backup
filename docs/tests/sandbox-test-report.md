# Sandbox Test Report

**Date:** 2026-02-26
**Python:** 3.12.7
**pytest:** 9.0.2
**Result:** 197 passed, 2 skipped, 0 failed

---

## Test files

| File | Tests | Coverage target |
|------|-------|-----------------|
| `tests/test_config.py` | 20 | `bbackup/config.py` (99%) |
| `tests/test_rotation.py` | 27 | `bbackup/rotation.py` (68%) |
| `tests/test_encryption.py` | 20 | `bbackup/encryption.py` (30%) |
| `tests/test_remote.py` | 13 | `bbackup/remote.py` (42%) |
| `tests/test_cli.py` | 27 | `bbackup/cli.py`, entry points |
| `tests/test_maintenance_stamp.py` | 33 | `maintenance/stamp.py` (71%) |
| `tests/test_maintenance_bump_version.py` | 37 | `maintenance/bump_version.py` (67%) |
| `tests/test_maintenance_check_docs.py` | 20 | `maintenance/check_docs.py` (65%) |

---

## Coverage summary

| Module | Stmts | Miss | Cover |
|--------|-------|------|-------|
| bbackup/__init__.py | 2 | 0 | 100% |
| bbackup/config.py | 109 | 1 | 99% |
| bbackup/logging.py | 30 | 1 | 97% |
| bbackup/rotation.py | 121 | 39 | 68% |
| bbackup/remote.py | 144 | 83 | 42% |
| bbackup/encryption.py | 363 | 254 | 30% |
| bbackup/cli.py | 385 | 312 | 19% |
| bbackup/backup_runner.py | 235 | 219 | 7% |
| bbackup/docker_backup.py | 225 | 201 | 11% |
| bbackup/restore.py | 198 | 178 | 10% |
| bbackup/tui.py | 334 | 304 | 9% |
| bbackup/management/__init__.py | 7 | 0 | 100% |
| maintenance/stamp.py | 104 | 30 | 71% |
| maintenance/bump_version.py | 160 | 53 | 67% |
| maintenance/check_docs.py | 96 | 34 | 65% |
| maintenance/release.py | 172 | 172 | 0% |
| **TOTAL** | **3680** | **2790** | **24%** |

HTML report: `docs/test-coverage/index.html`

---

## What is tested

### `bbackup/config.py` (99%)

- All dataclass defaults (BackupScope, RetentionPolicy, IncrementalSettings, EncryptionSettings, RemoteStorage)
- Config with no file path: loads defaults, correct staging dir, empty backup sets / remotes
- Config from full YAML: retention, scope, incremental, backup sets (name, description, containers, scope), remotes, enabled remotes filter, staging dir, get_backup_set by name
- Error cases: malformed YAML raises ValueError, empty YAML loads defaults, partial retention fills remaining defaults, disabled remote excluded from enabled list

### `bbackup/rotation.py` (68%)

- Age categorization: today, yesterday, 6d (daily), 7d and 20d (weekly), 30d and 90d (monthly)
- `should_keep_backup`: recent, Sunday weekly, first-of-month monthly
- `_parse_backup_date`: standard format, extra prefix parts, unparseable, empty string, invalid date (month 13)
- `filter_backups_by_retention`: daily limit cap, excess deleted, keep + delete == total, empty list, unparseable names excluded
- Storage quota: disabled when max 0, enabled when max set, no warning on low usage
- `_calculate_local_storage`: empty dir, single-level files, nested files, nonexistent path

### `bbackup/encryption.py` (30%)

- EncryptionManager construction: disabled config, symmetric with no key / missing key file / valid key file, asymmetric with no keys
- AES-256-GCM: encrypt/decrypt roundtrip, nonce uniqueness, wrong-key failure (InvalidTag), tampered ciphertext, AAD enforcement, 32-byte key requirement
- File encrypt/decrypt roundtrip (via `encrypt_file` / `decrypt_file`, skipped if not implemented)
- RSA 2048-bit key generation, public key extraction, PEM serialization/deserialization roundtrip
- URL detection helpers: `_is_url` (HTTP, HTTPS, file path), `_is_github_shortcut`

### `bbackup/remote.py` (42%)

- `upload_to_local`: single file, directory (recursive), creates missing dest, overwrites existing
- `_list_local_backups`: lists directories only, empty dir, nonexistent path
- `list_backups` dispatch: local -> `_list_local_backups`, SFTP -> empty
- `upload_backup` dispatch: local type, unknown type returns False, rclone binary check, rclone without remote_name

### `bbackup/cli.py` (19%)

- All modules importable: bbackup, config, cli, backup_runner, docker_backup, restore, remote, rotation, tui, encryption, management
- Package attributes: `__version__` (semver), `__author__` (str)
- `--help` for: main, backup, restore, list-containers, init-config, list-backups
- `--version` flag
- All 5 expected commands registered (backup, restore, list-containers, init-config, list-backups)
- `bbackup.py` entry point: `--help` and `--version` via subprocess
- Management API callables: run_health_check, is_first_run, check_for_updates, run_setup_wizard

### `maintenance/stamp.py` (71%)

- `load_config`: valid file, missing file raises SystemExit, custom path via PROJECT_YAML
- `build_footer`: contains author, company name, company URL, year, license, FOOTER sentinels, `align="center"`, license URL links to repo LICENSE file
- `stamp_file`: stamps new file, idempotent (second stamp returns "unchanged"), single sentinel block after two stamps, dry_run no-op, missing file returns "skipped", replaces outdated footer, preserves content above footer
- `sync_code_files`: updates LICENSE copyright line, dry_run skips write, missing LICENSE returns "skipped"
- `stamp_docs`: stamps multiple files in one call, skips missing target

### `maintenance/bump_version.py` (67%)

- `parse_semver`: basic, zeros, large numbers, missing patch raises, non-numeric raises
- `bump`: patch, minor (resets patch), major (resets minor+patch), on zero inputs
- `determine_bump_type`: feat->minor, feat(scope)->minor, fix->patch, docs->patch, chore->patch, BREAKING CHANGE->major, feat!->major, mixed feat+fix->minor, empty->patch, unrecognized->patch
- `read_version` / `write_version` / round-trip
- `sync_version_in_file`: updates `__version__`, already-current no-op, no pattern match, missing file, package.json style
- `generate_changelog_entry`: version header, today date, feat->Added, fix->Fixed, docs->Documentation, chore->Maintenance, bump commit excluded, empty messages fallback, subject capitalized
- `prepend_changelog`: new section prepended, dry_run no-op, missing CHANGELOG skips gracefully

### `maintenance/check_docs.py` (65%)

- `match_glob`: exact, wildcard, recursive wildcard, no match, multiple patterns, empty list
- `check_internal_links`: no links, valid relative link, broken relative link, HTTP links skipped, anchor links skipped, mixed links, link with fragment, missing doc file
- `DocCheckResult`: default ok=True, can hold broken_links, can hold docs_to_review
- `run()` (with patched `get_changed_files`): no changed files is ok, detects broken link, flags stale docs, all clean returns ok

---

## Skipped tests (2)

Both skipped because private helpers (`_encrypt_data`, `_decrypt_data`) are not exposed on `EncryptionManager`. The corresponding `encrypt_file`/`decrypt_file` roundtrip test passed. No action needed.

---

## Coverage gaps (what is NOT tested)

These modules require a live Docker daemon and cannot be meaningfully unit-tested without integration fixtures:

- `bbackup/backup_runner.py` (7%) - Docker container/volume orchestration
- `bbackup/docker_backup.py` (11%) - Docker API calls
- `bbackup/restore.py` (10%) - Docker container/volume restore
- `bbackup/tui.py` (9%) - Rich terminal UI rendering
- `maintenance/release.py` (0%) - Full release workflow (git operations, real filesystem)

These would require either a Docker-in-Docker test environment or extensive mocking of the Docker SDK. Recommended next step: integration test suite using `pytest-docker` or a dedicated test container.

---

## Findings

No bugs found. All tested logic behaves as designed. One style note: `upload_backup` in `remote.py` has a duplicated docstring (line 196-197) which is cosmetic only.

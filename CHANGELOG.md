# Changelog

All notable changes to this project will be documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). This project uses [semantic versioning](https://semver.org/).

---

## [Unreleased]

### Added

- Filesystem backup: back up arbitrary host paths and directory trees with rsync, gitignore-style exclude patterns, and incremental `--link-dest` support
- New `bbackup/filesystem_backup.py` module with `FilesystemBackup` class
- `FilesystemTarget` and `FilesystemBackupSet` dataclasses in `config.py`
- `filesystems:` section in `config.yaml.example` with annotated examples
- `--paths`, `--exclude`, `--filesystem-set` options on `bbackup backup`
- `--filesystem`, `--filesystem-destination` options on `bbackup restore`
- `bbackup list-filesystem-sets` subcommand
- Filesystem panel in live TUI dashboard (third column alongside containers and volumes)

---

## [1.2.1] - 2026-02-26

### Changed

- Expanded test coverage from 59% to 76% across all core modules
- Resolved all ruff lint violations in the `bbackup` package

### Fixed

- `BackupRunner._parse_rsync_progress` hoisted from closure to method for reuse
- `BackupStatus.update()` no longer receives `transfer_speed` as a kwarg (set directly)

---

## [1.2.0] - 2026-02-26

### Added

- Full CI testing suite: 289 unit tests covering all `bbackup/` modules
- `scripts/run_tests.py` agentic sandbox test runner with Docker isolation and self-healing debug loop
- `Dockerfile.test` for sandboxed test execution
- `requirements-dev.txt` with pytest, pytest-cov, pytest-mock
- GitHub Actions CI workflow with unit and integration test jobs
- LICENSE file (MIT)
- CHANGELOG.md following Keep a Changelog format
- Community health files: CONTRIBUTING.md, CODE_OF_CONDUCT.md, issue templates, PR template
- Project identity system: copyright footer stamped across all public-facing docs
- `maintenance/release.py` automated release workflow with doc validation
- `maintenance/check_docs.py` stale-doc detection with agent-driven auto-update support
- `maintenance/bump_version.py` conventional-commit version bumping

---

## [1.1.0] - 2026-02-26

### Added

- Rich TUI with BTOP-style live dashboard and real-time transfer metrics (speed, bytes, file count, ETA)
- Docker backup for containers, volumes, networks, and configuration metadata
- Incremental backups using rsync `--link-dest` (hardlinks unchanged files instead of copying)
- AES-256-GCM symmetric encryption at rest
- RSA-4096 / ECDSA P-384 asymmetric encryption with public/private key separation
- GitHub key hosting: reference public keys by `github:USERNAME/gist:ID` shortcut
- Remote storage: Google Drive via rclone, SFTP via paramiko, local directory
- Time-based backup rotation with daily/weekly/monthly retention and storage quota enforcement
- Full restore of containers, volumes, and networks with optional rename on restore
- Backup sets: named container groups defined in config for repeatable runs
- Selective backup: `--config-only`, `--volumes-only`, `--no-networks` flags
- `bbman` management CLI: setup wizard, health checks, dependency management, diagnostics, self-update
- Interactive container selection with TUI dialog
- Keyboard controls in TUI: Q (quit), P (pause/resume), S (skip), H (help)
- YAML configuration with priority chain and CLI override support
- Rotating file logger via `get_logger()` factory

### Changed

- Project structured for standalone GitHub distribution

---

[Unreleased]: https://github.com/cptnfren/best-backup/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/cptnfren/best-backup/releases/tag/v1.1.0

<!-- project-footer:start -->

<br><br>

<p align="center">
Slavic Kozyuk<br>
&copy; 2026 <a href="https://www.cruxexperts.com/">Crux Experts LLC</a> &mdash; <a href="https://github.com/cptnfren/best-backup/blob/main/LICENSE">MIT License</a>
</p>

<!-- project-footer:end -->

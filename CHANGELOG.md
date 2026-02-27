# Changelog

All notable changes to this project will be documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). This project uses [semantic versioning](https://semver.org/).

---

## [Unreleased]

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

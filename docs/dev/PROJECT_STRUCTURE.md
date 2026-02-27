# Project Structure - bbackup

This document describes the organization and structure of the bbackup project repository.

## Directory Structure

```
best-backup/
├── .cursor/                    # Cursor AI rules (auto-loaded, not tracked in git)
│   └── rules/                 # Rule files for AI agents
│       ├── bbackup.mdc        # Consolidated project rules (always applied)
│       └── localsetup-context.mdc  # Localsetup framework context
│
├── bbackup/                   # Main Python package
│   ├── __init__.py           # Package metadata and version
│   ├── cli.py                # bbackup CLI commands and entry point
│   ├── config.py             # Configuration loading, parsing, all dataclasses
│   ├── docker_backup.py      # Docker backup via temp containers
│   ├── backup_runner.py      # Backup workflow orchestration + BackupStatus
│   ├── restore.py            # Restore operations
│   ├── tui.py                # Rich TUI, live dashboard, BackupStatus class
│   ├── remote.py             # Remote storage integration (local/rclone/SFTP)
│   ├── rotation.py           # Backup rotation and retention logic
│   ├── encryption.py         # AES-256-GCM + RSA/ECDSA encryption
│   ├── logging.py            # Rotating file logging, get_logger() factory
│   ├── bbman_entry.py        # Console script shim for bbman
│   └── management/           # Lifecycle management subpackage
│       ├── first_run.py      # First-run detection and config path
│       ├── setup_wizard.py   # Interactive first-time setup wizard
│       ├── health.py         # Docker/system health checks
│       ├── diagnostics.py    # Diagnostic report generation
│       ├── dependencies.py   # External dependency checks/install
│       ├── updater.py        # Self-update from repo
│       ├── version.py        # Version check, checksum computation
│       ├── repo.py           # Repo URL management
│       ├── config.py         # Management-layer config (separate from backup)
│       ├── status.py         # Status reporting utilities
│       ├── cleanup.py        # Temp file and stale resource cleanup
│       └── utils.py          # Shared management utilities
│
├── docs/                      # Development documentation
│   ├── README.md             # Documentation index
│   ├── TUI_IMPROVEMENTS.md   # TUI development notes
│   ├── ENCRYPTION_GUIDE.md   # Encryption usage guide
│   ├── GITHUB_KEY_EXAMPLES.md # GitHub key deployment examples
│   ├── PROJECT_STRUCTURE.md  # This file
│   ├── REORGANIZATION_SUMMARY.md # Reorganization history
│   ├── reports/              # Deficiency and analysis reports
│   │   ├── DEFICIENCY_REPORT.md
│   │   ├── FEATURE_STATUS_REPORT.md
│   │   ├── CODE_ANALYSIS_REPORT.md
│   │   ├── QUICK_DEFICIENCY_SUMMARY.md
│   │   ├── IMPLEMENTATION_ROADMAP.md
│   │   ├── IMPLEMENTATION_COMPLETE.md
│   │   └── REPORTS_INDEX.md
│   └── tests/                # Test results and reports
│       ├── TEST_RESULTS.md
│       ├── TEST_RESULTS_COMPREHENSIVE.md
│       ├── SANDBOX_BACKUP_TEST_LOG.md
│       ├── ENCRYPTION_TEST_LOG.md
│       └── ENCRYPTION_SETUP_SUMMARY.md
│
├── scripts/                   # Utility scripts
│   ├── README.md             # Scripts documentation
│   ├── populate_postgres.sh  # Test data population script
│   └── test_backup_with_locks.sh  # Lock testing script
│
├── bbackup.py                # bbackup entry point script
├── bbman.py                  # bbman management CLI
├── config.yaml.example       # Example configuration file
├── requirements.txt          # Python dependencies
├── setup.py                  # Package setup for distribution
├── .gitignore               # Git ignore rules
│
├── README.md                 # Main user documentation
├── QUICKSTART.md            # Quick start guide
├── QUICK_INSTALL.md         # Installation guide
├── INSTALL.md               # Detailed installation guide
└── PROJECT_SUMMARY.md       # Architecture and design overview
```

## Directory Purposes

### Root Directory
- **User-facing files:** README.md, QUICKSTART.md, PROJECT_SUMMARY.md
- **Essential files:** bbackup.py, requirements.txt, setup.py, config.yaml.example
- **Package directory:** bbackup/ (main source code)

### `.cursor/rules/`
Contains consolidated Cursor AI agent rules. Not tracked in git (`.cursor/` is gitignored). Two files: `bbackup.mdc` (all project rules, always applied) and `localsetup-context.mdc` (framework context).

### `bbackup/`
Main Python package. Each module has a specific responsibility:
- `cli.py` - bbackup CLI commands, arg parsing, orchestration
- `config.py` - Config load/parse/validate, all dataclasses
- `docker_backup.py` - Docker API, backup via temp Alpine containers
- `backup_runner.py` - Workflow orchestration, `BackupStatus` tracking
- `restore.py` - Volume/container/network restore
- `tui.py` - Rich live dashboard, `BackupStatus` class
- `remote.py` - Upload/download abstraction (local/rclone/SFTP)
- `rotation.py` - Retention policies, quota cleanup
- `encryption.py` - AES-256-GCM + RSA/ECDSA encryption, key management
- `logging.py` - `get_logger()` factory, rotating file handler setup
- `bbman_entry.py` - Console script shim for the `bbman` command
- `management/` - Lifecycle subpackage (first-run, health, updates, diagnostics, etc.)

### `docs/`
Development and technical documentation:
- **reports/:** Deficiency analysis, feature status, code analysis, implementation reports
- **tests/:** Test results, verification reports, encryption testing logs
- **TUI_IMPROVEMENTS.md:** TUI development notes
- **ENCRYPTION_GUIDE.md:** Encryption usage and configuration guide
- **GITHUB_KEY_EXAMPLES.md:** GitHub key deployment examples
- **PROJECT_STRUCTURE.md:** Repository structure documentation (this file)

### `scripts/`
Utility scripts for testing and development:
- Shell scripts for test data setup
- Testing utilities
- Development helpers

## File Organization Rules

### Source Code
- All Python source code in `bbackup/` package
- One module per major feature/concern
- Descriptive module names (verb_noun.py pattern)

### Documentation
- **User docs:** Root directory (README.md, QUICKSTART.md, QUICK_INSTALL.md, PROJECT_SUMMARY.md)
- **Development docs:** `docs/` directory (TUI_IMPROVEMENTS.md, ENCRYPTION_GUIDE.md, etc.)
- **Reports:** `docs/reports/` subdirectory
- **Test results:** `docs/tests/` subdirectory

### Scripts
- All utility scripts in `scripts/` directory
- Scripts should be executable
- Include README.md explaining script purposes

### Configuration
- Example config: `config.yaml.example` in root
- User configs: `~/.config/bbackup/config.yaml` (not tracked)

## Naming Conventions

### Python Files
- Lowercase with underscores: `backup_runner.py`
- Descriptive names matching module purpose
- One class/concern per file when possible

### Documentation Files
- UPPERCASE for main docs: `README.md`, `PROJECT_SUMMARY.md`
- Descriptive names for reports: `DEFICIENCY_REPORT.md`
- Keep in appropriate subdirectories

### Scripts
- Lowercase with underscores: `populate_postgres.sh`
- Descriptive names indicating purpose
- Executable permissions set

## Adding New Files

### New Python Module
1. Add to `bbackup/` package
2. Follow naming convention
3. Update `__init__.py` if needed
4. Add to appropriate Cursor rule file

### New Documentation
1. Determine if user-facing or development
2. Place in root (user) or `docs/` (development)
3. Use appropriate subdirectory if needed
4. Update relevant README.md files

### New Script
1. Add to `scripts/` directory
2. Make executable: `chmod +x scripts/script_name.sh`
3. Update `scripts/README.md`
4. Document purpose and usage

## Maintenance

- Keep structure organized according to these rules
- Update this document when structure changes
- Maintain README files in each directory
- Follow Cursor rules for consistency

---

**Last Updated:** 2026-01-08

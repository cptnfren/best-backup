# Project Structure - bbackup

This document describes the organization and structure of the bbackup project repository.

## Directory Structure

```
best-backup/
├── .cursor/                    # Cursor AI rules (auto-loaded)
│   └── rules/                 # Rule files for AI agents
│       ├── project_overview.mdc
│       ├── code_organization.mdc
│       ├── error_handling.mdc
│       ├── docker_backup.mdc
│       ├── tui_patterns.mdc
│       ├── configuration.mdc
│       ├── remote_storage.mdc
│       ├── backup_rotation.mdc
│       ├── workflow.mdc
│       ├── testing.mdc
│       └── documentation.mdc
│
├── bbackup/                   # Main Python package
│   ├── __init__.py           # Package metadata and version
│   ├── cli.py                # CLI commands and entry point
│   ├── config.py             # Configuration loading and parsing
│   ├── docker_backup.py      # Docker backup operations
│   ├── backup_runner.py      # Backup orchestration with status tracking
│   ├── restore.py            # Restore operations
│   ├── tui.py                # Rich TUI interface and status display
│   ├── remote.py              # Remote storage integration
│   └── rotation.py           # Backup rotation and retention logic
│
├── docs/                      # Development documentation
│   ├── README.md             # Documentation index
│   ├── TUI_IMPROVEMENTS.md   # TUI development notes
│   ├── reports/              # Deficiency and analysis reports
│   │   ├── DEFICIENCY_REPORT.md
│   │   ├── FEATURE_STATUS_REPORT.md
│   │   ├── CODE_ANALYSIS_REPORT.md
│   │   ├── QUICK_DEFICIENCY_SUMMARY.md
│   │   ├── IMPLEMENTATION_ROADMAP.md
│   │   └── REPORTS_INDEX.md
│   └── tests/                # Test results and reports
│       ├── TEST_RESULTS.md
│       └── TEST_RESULTS_COMPREHENSIVE.md
│
├── scripts/                   # Utility scripts
│   ├── README.md             # Scripts documentation
│   ├── populate_postgres.sh  # Test data population script
│   └── test_backup_with_locks.sh  # Lock testing script
│
├── bbackup.py                # Main executable script (CLI entry point)
├── config.yaml.example       # Example configuration file
├── requirements.txt          # Python dependencies
├── setup.py                  # Package setup for distribution
├── .gitignore               # Git ignore rules
│
├── README.md                 # Main user documentation
├── QUICKSTART.md            # Quick start guide
├── PROJECT_SUMMARY.md       # Architecture and design overview
└── PROJECT_STRUCTURE.md     # This file
```

## Directory Purposes

### Root Directory
- **User-facing files:** README.md, QUICKSTART.md, PROJECT_SUMMARY.md
- **Essential files:** bbackup.py, requirements.txt, setup.py, config.yaml.example
- **Package directory:** bbackup/ (main source code)

### `.cursor/rules/`
Contains Cursor AI agent rules organized by topic. These files automatically guide AI agents working on the codebase.

### `bbackup/`
Main Python package containing all source code. Each module has a specific responsibility:
- `cli.py` - Command-line interface
- `config.py` - Configuration management
- `docker_backup.py` - Docker operations
- `backup_runner.py` - Backup workflow orchestration
- `restore.py` - Restore operations
- `tui.py` - Terminal user interface
- `remote.py` - Remote storage integration
- `rotation.py` - Backup rotation logic

### `docs/`
Development and technical documentation:
- **reports/:** Deficiency analysis, feature status, code analysis
- **tests/:** Test results and verification reports
- **TUI_IMPROVEMENTS.md:** TUI development notes

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
- **User docs:** Root directory (README.md, QUICKSTART.md)
- **Development docs:** `docs/` directory
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

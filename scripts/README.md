# Scripts Directory

Utility scripts for testing and development.

## Available Scripts

### `create_sandbox.py`
Generates a comprehensive testing sandbox filesystem with diverse file types, realistic directory structures, and safely harvested system files. Perfect for testing backup, restore, and incremental backup operations.

**Features:**
- Creates 13,000+ files across diverse file types
- Generates realistic directory structures (archives, projects, documents, media)
- Safely harvests system files (read-only, no modifications)
- Real-time progress reporting with Rich library
- Configurable via CLI arguments or YAML config file
- Generates comprehensive README.md report

**Quick Start:**
```bash
# Default sandbox (minimal input)
python scripts/create_sandbox.py --output /tmp/bbackup_sandbox

# Quick mode (fewer files, faster)
python scripts/create_sandbox.py --output /tmp/bbackup_sandbox --quick

# Custom configuration
python scripts/create_sandbox.py --output /tmp/test_sandbox --file-count 5000

# With config file
python scripts/create_sandbox.py --config scripts/sandbox_config.yaml
```

**Options:**
- `--output, -o` - Output directory (default: `/tmp/bbackup_sandbox`)
- `--config, -c` - Configuration file path (YAML)
- `--file-count` - Target total file count
- `--size-mb` - Target total size in MB
- `--harvest-system/--no-harvest-system` - Enable/disable system file harvesting
- `--quick` - Quick mode (fewer files, faster generation)
- `--verbose, -v` - Verbose output

**Configuration File:**
See `sandbox_config.yaml.example` for advanced configuration options including:
- File counts per category
- Directory structure customization
- Large file sizes
- System file harvesting paths

**Output:**
- Creates sandbox directory with diverse file structure
- Generates `README.md` with complete statistics
- Provides real-time progress updates during generation
- Safe file harvesting (read-only, originals untouched)

### `populate_postgres.sh`
Populates a PostgreSQL test container with sample data for testing backup/restore operations.

**Usage:**
```bash
./scripts/populate_postgres.sh
```

### `test_backup_with_locks.sh`
Tests backup operations with active database locks to verify backup integrity during concurrent operations.

**Usage:**
```bash
./scripts/test_backup_with_locks.sh
```

### `test_sandbox_backups.py`
Automated test script to run various backup scenarios against the sandbox and log issues.

**Usage:**
```bash
python scripts/test_sandbox_backups.py
```

### `get_github_key.sh`
Helper script to fetch SSH public keys from a GitHub user profile.

**Usage:**
```bash
./scripts/get_github_key.sh USERNAME
```

### `upload_key_to_github.sh`
Helper script to upload encryption keys to GitHub gist.

**Usage:**
```bash
./scripts/upload_key_to_github.sh /path/to/key.pem
```

## Notes

- All scripts are executable and can be run directly
- Scripts are designed for testing and development purposes
- Ensure Docker is running before executing database-related scripts
- `create_sandbox.py` requires Python 3.8+ and dependencies from requirements.txt
- Python scripts require dependencies from `requirements.txt`
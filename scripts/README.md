# Scripts Directory

Utility scripts for testing and development.

## Available Scripts

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

## Notes

- All scripts are executable and can be run directly
- Scripts are designed for testing and development purposes
- Ensure Docker is running before executing scripts

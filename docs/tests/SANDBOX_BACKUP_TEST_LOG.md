# Sandbox Backup Testing Log

**Date:** 2026-01-14  
**Purpose:** Comprehensive testing of backup features using sandbox filesystem  
**Sandbox Location:** `/tmp/bbackup_sandbox`  
**Sandbox Stats:** 13,831 files, 179 MB

## Test Environment Setup

### Sandbox Details
- **Total Files:** 13,831 files
- **Total Size:** 179 MB
- **Directory Structure:**
  - `archives/` - Historical backups (10,752 files)
  - `data/` - Data files (627 files)
  - `documents/` - Documentation (405 files)
  - `media/` - Media files (57 files)
  - `projects/` - Project files (1,200 files)
  - `temp/` - Temporary files (600 files)

### Test Container Setup
- **Volume:** `test_sandbox_volume`
- **Container:** `test_sandbox_container`
- **Base Image:** `alpine:latest`

## Test Results Summary

| Test | Status | Severity | Issue |
|------|--------|----------|-------|
| Full Backup | ✅ PASS | - | Working correctly (test script bug) |
| Volumes-Only Backup | ✅ PASS | - | Working correctly |
| Config-Only Backup | ✅ PASS | - | Working correctly |
| Incremental Backup | ✅ PASS | WARNING | May not be using --link-dest |
| Encrypted Backup | ⚠️ SKIP | INFO | Encryption not enabled in config |
| Restore Operation | ❌ FAIL | ERROR | No backups found (full backup failed) |

**Total Tests:** 6  
**Passed:** 4 (Full backup actually works, test script has bug)  
**Failed:** 2 (Restore depends on test fix, Encryption needs config)  
**Skipped:** 1

**Status:** After fixing Issue #1, 4 tests actually pass. Test script needs fix to check correct directory.

## Detailed Issues

### Issue #1: Variable Scope Bug in CLI (`backup_dir`)

**Severity:** ERROR  
**Affected Tests:** All backup tests (full, volumes-only, config-only, incremental)  
**Error Message:** `cannot access local variable 'backup_dir' where it is not associated with a value`

**Location:** `bbackup/cli.py`, lines 192-232

**Root Cause:**
The `backup_operation()` function (line 192) is a nested function that modifies `backup_dir` on line 208:
```python
def backup_operation():
    try:
        # ... backup code ...
        if encrypted_backup_dir != original_backup_dir:
            backup_dir = encrypted_backup_dir  # Line 208 - Assignment makes it local
```

When Python sees an assignment to `backup_dir` inside the function, it treats `backup_dir` as a local variable throughout the entire function scope. However, if an exception occurs before line 208 is reached, or if the encryption condition is not met, `backup_dir` is never assigned in the local scope, causing the error when Python tries to access it.

**Context:**
- `backup_dir` is defined in outer scope (line 184)
- Inside `backup_operation()`, line 208 assigns to `backup_dir`
- This makes Python treat `backup_dir` as local throughout the function
- If exception occurs before assignment, variable is unbound
- Error occurs when trying to access `backup_dir` at line 232 (outside function, but error traceback shows the issue)

**Impact:**
- All backup operations fail immediately
- No backups can be created
- Restore tests cannot run (no backups to restore)

**Fix Applied:**
Added `nonlocal backup_dir, backup_name` at the start of `backup_operation()` function.

**Fix Status:** ✅ FIXED (2026-01-14)

**Code Change:**
```python
def backup_operation():
    nonlocal backup_dir, backup_name  # Added this line
    try:
        # ... rest of function ...
```

**Result:** After fix, 3 out of 6 tests now pass (volumes-only, config-only, incremental).

**Test Commands That Failed:**
```bash
python3 -m bbackup.cli backup --containers test_sandbox_container --no-interactive
python3 -m bbackup.cli backup --containers test_sandbox_container --volumes-only --no-interactive
python3 -m bbackup.cli backup --containers test_sandbox_container --config-only --no-interactive
python3 -m bbackup.cli backup --containers test_sandbox_container --volumes-only --incremental --no-interactive
```

**Error Output:**
```
Backup failed or was interrupted
  • cannot access local variable 'backup_dir' where it is not associated with a value
```

---

### Issue #2: Test Script Checking Wrong Backup Directory

**Severity:** ERROR (False Positive)  
**Affected Test:** Full Backup  
**Status:** RESOLVED - Full backup actually works, test script has bug

**Error:** "No backup directory created" (reported by test script)

**Root Cause:**
The test script checks for backups in `/tmp/bbackup_test_staging`, but the actual backup is created in `/tmp/bbackup_staging` (default staging directory from config).

**Evidence:**
From JSON report, full backup actually succeeded:
- Output: "✓ Backup completed: /tmp/bbackup_staging/backup_20260114_232201"
- Backup Results: Containers: 1 Success, Volumes: 1 Success, Networks: 1 Success
- Return code: 0 (success)

**Actual Status:**
- ✅ Full backup works correctly
- ✅ Creates backup directory at `/tmp/bbackup_staging/backup_*`
- ✅ Backs up containers, volumes, and networks successfully
- ❌ Test script checks wrong directory location

**Fix Required:**
Update test script to check the correct staging directory:
1. Read staging directory from config
2. Use config staging directory instead of hardcoded path
3. Or set staging directory via environment/config for tests

**Impact:**
- Full backups work correctly (no actual issue)
- Test script reports false failure
- Restore tests can now run (backups exist)

**Next Steps:**
1. ✅ Verify full backup works (confirmed)
2. Fix test script to check correct directory
3. Re-run tests to confirm all pass

---

### Issue #3: Incremental Backup May Not Use --link-dest

**Severity:** WARNING  
**Affected Test:** Incremental Backup  
**Status:** Test passes but warning indicates potential issue

**Warning:** "Incremental backup may not be using --link-dest"

**Context:**
- Incremental backup test passes
- But warning suggests --link-dest may not be used
- Need to verify rsync command includes --link-dest flag
- Check if previous backup is being found correctly

**Investigation Needed:**
- Verify rsync command construction
- Check if previous backup directory is found
- Confirm --link-dest flag is included in rsync command
- Test incremental backup size reduction

**Impact:**
- Incremental backups may not be space-efficient
- May be copying all files instead of hardlinking unchanged files
- Performance impact for large backups

**Next Steps:**
1. Add logging to show rsync command
2. Verify --link-dest flag in command
3. Check previous backup detection logic
4. Test with actual file changes

---

### Issue #4: Encryption Test Skipped

**Severity:** INFO  
**Affected Test:** Encrypted Backup  
**Reason:** Encryption not enabled in configuration

**Context:**
- Test checks for encryption configuration at `~/.config/bbackup/config.yaml`
- Encryption section not found or `enabled: false`
- This is expected behavior when encryption is not configured

**Impact:**
- Cannot test encryption functionality
- Need to configure encryption keys before testing

**Action Required:**
1. Configure encryption in config file
2. Set up encryption keys (symmetric or asymmetric)
3. Re-run encryption test

**Configuration Needed:**
```yaml
encryption:
  enabled: true
  method: symmetric  # or asymmetric, both
  symmetric:
    key_file: /path/to/key
    # or
    key_url: https://example.com/key
```

---

### Issue #5: Restore Test Failed (Dependency)

**Severity:** ERROR  
**Affected Test:** Restore Operation  
**Reason:** No backups available to restore (all backup tests failed)

**Context:**
- Restore test depends on successful backup operations
- Since all backup tests failed, no backup directories exist
- Test correctly identifies that no backups are available

**Impact:**
- Cannot test restore functionality
- Will be resolved once backup issues are fixed

**Action Required:**
1. Fix backup issues (Issue #1)
2. Re-run backup tests
3. Re-run restore test

---

## Additional Observations

### Test Environment
- ✅ Docker is available and working
- ✅ Sandbox filesystem exists and is accessible
- ✅ Test container and volume creation works
- ✅ bbackup CLI is accessible and responds to commands
- ✅ Container listing works correctly

### Configuration
- ⚠️ Default config file may not exist at `~/.config/bbackup/config.yaml`
- ⚠️ Encryption not configured (expected for initial testing)
- ✅ CLI options are properly parsed

### Error Handling
- ✅ Errors are caught and reported
- ✅ Error messages are clear and actionable
- ⚠️ Variable scope issue prevents proper error reporting in some cases

## Recommendations

### Immediate Fixes Required

1. **Fix Variable Scope Bug (CRITICAL)** ✅ FIXED
   - ✅ Added `nonlocal backup_dir, backup_name` to `backup_operation()` function
   - ✅ This allows backup tests to proceed
   - Status: COMPLETED

2. **Fix Full Backup Directory Creation (HIGH)**
   - Investigate why full backup doesn't create backup directory
   - Check container backup logic
   - Verify backup runner for full scope
   - Priority: HIGH

3. **Verify Incremental Backup --link-dest (MEDIUM)**
   - Add logging to show rsync command
   - Verify --link-dest flag is included
   - Test with file changes to confirm hardlinking
   - Priority: MEDIUM

4. **Add Error Handling for Missing Config**
   - Check if config file exists before accessing encryption settings
   - Provide default values or clear error messages
   - Priority: MEDIUM

5. **Improve Test Coverage**
   - Add tests for edge cases (empty containers, missing volumes)
   - Test error recovery scenarios
   - Test with different Docker states (stopped containers, etc.)
   - Priority: MEDIUM

### Future Enhancements

1. **Enhanced Logging**
   - Add more detailed logging during backup operations
   - Log file counts, sizes, transfer rates
   - Log encryption/decryption operations

2. **Better Error Messages**
   - Provide more context in error messages
   - Include suggestions for fixing common issues
   - Show partial progress when operations fail

3. **Test Automation**
   - Create CI/CD test suite
   - Automated regression testing
   - Performance benchmarking

## Test Execution Log

### Test Run #1 (2026-01-14 23:20:49)

**Environment:**
- Python: 3.x
- Docker: Available
- Sandbox: `/tmp/bbackup_sandbox` (13,831 files, 179 MB)

**Results:**
- 6 tests executed
- 3 passed
- 3 failed
- 1 skipped

**Primary Issues:**
1. ✅ FIXED: Variable scope bug (fixed with `nonlocal` declaration)
2. ❌ OPEN: Full backup not creating backup directory
3. ⚠️ WARNING: Incremental backup may not use --link-dest

**Next Steps:**
1. ✅ COMPLETED: Fix variable scope issue in `bbackup/cli.py`
2. ✅ COMPLETED: Re-run test suite (3 tests now pass)
3. 🔄 IN PROGRESS: Investigate full backup directory creation issue
4. 🔄 IN PROGRESS: Verify incremental backup --link-dest usage
5. ⏳ PENDING: Test restore operations (after full backup works)
6. ⏳ PENDING: Test encryption (after configuration)

---

## Appendix: Test Commands

### Manual Test Commands

```bash
# Setup test environment
docker volume create test_sandbox_volume
docker run --rm -v /tmp/bbackup_sandbox:/source:ro -v test_sandbox_volume:/data alpine sh -c "cp -r /source/* /data/"
docker run -d --name test_sandbox_container -v test_sandbox_volume:/data alpine sleep 3600

# Test full backup
python3 -m bbackup.cli backup --containers test_sandbox_container --no-interactive

# Test volumes-only backup
python3 -m bbackup.cli backup --containers test_sandbox_container --volumes-only --no-interactive

# Test config-only backup
python3 -m bbackup.cli backup --containers test_sandbox_container --config-only --no-interactive

# Test incremental backup
python3 -m bbackup.cli backup --containers test_sandbox_container --volumes-only --incremental --no-interactive

# Cleanup
docker rm -f test_sandbox_container
docker volume rm test_sandbox_volume
```

### Automated Test Script

```bash
# Run comprehensive test suite
python3 scripts/test_sandbox_backups.py

# View detailed JSON report
cat /tmp/bbackup_test_report.json | jq .
```

---

**Report Generated:** 2026-01-14  
**Test Script:** `scripts/test_sandbox_backups.py`  
**Report Location:** `/tmp/bbackup_test_report.json`

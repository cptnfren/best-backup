#!/usr/bin/env python3
# Purpose: Verify Cursor context file exists.
# Created: 2026-02-20

import sys
from pathlib import Path

_ENGINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ENGINE))
from lib.path_resolution import get_project_root

def main():
    root = get_project_root()
    mdc = root / ".cursor" / "rules" / "localsetup-context.mdc"
    print("Localsetup v2 - Context Verification")
    print("=====================================")
    if mdc.is_file():
        print("[OK] .cursor/rules/localsetup-context.mdc exists (%s bytes)" % mdc.stat().st_size)
    else:
        sys.stderr.write("[FAIL] No .cursor/rules/localsetup-context.mdc found. Run install then deploy for Cursor.\n")
        return 1
    print("[OK] Context verification complete.")
    return 0

if __name__ == "__main__":
    sys.exit(main())

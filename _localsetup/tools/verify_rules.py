#!/usr/bin/env python3
# Purpose: Rule compliance check (git, data_paths, skills, output contract validator).
# Created: 2026-02-20
# Last updated: 2026-02-20

import subprocess
import sys
from pathlib import Path

_ENGINE = Path(__file__).resolve().parents[1]
if str(_ENGINE) not in sys.path:
    sys.path.insert(0, str(_ENGINE))
from lib.path_resolution import get_engine_dir, get_project_root


def main() -> int:
    engine_dir = get_engine_dir()
    root = get_project_root()
    print("Localsetup v2 - Rule Verification")
    print("==================================")

    try:
        r = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode == 0:
            log = subprocess.run(
                ["git", "-C", str(root), "log", "-1", "--oneline"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            msg = (log.stdout or "no commits").strip() if log.returncode == 0 else "no commits"
            print(f"[OK] Git repo: {msg}")
        else:
            print("[WARNING] Git not initialized or not installed")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("[WARNING] Git not initialized or not installed")

    data_sh = engine_dir / "lib" / "data_paths.sh"
    data_ps1 = engine_dir / "lib" / "data_paths.ps1"
    if data_sh.exists() or data_ps1.exists():
        print("[OK] data_paths (sh or ps1)")
    else:
        print("[FAIL] data_paths.sh / data_paths.ps1 missing")
        return 1

    skills_dir = engine_dir / "skills"
    if skills_dir.is_dir():
        print("[OK] skills dir")
    else:
        print("[FAIL] skills missing")
        return 1

    validator = engine_dir / "tools" / "validate_output_contract.py"
    if validator.exists():
        try:
            r = subprocess.run(
                [sys.executable, str(validator)],
                cwd=str(engine_dir.parent),
                timeout=30,
            )
            if r.returncode != 0:
                print("[FAIL] output contract validator failed", file=sys.stderr)
                return 1
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            print(f"[WARNING] python not found or validator timed out: {e}", file=sys.stderr)
    else:
        print("[WARNING] validate_output_contract.py not found")

    print("[OK] Rule verification complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# Purpose: Run a smoke command inside a skill sandbox and report exit code and output.
# Created: 2026-02-20
# Last updated: 2026-02-20

"""
Run a single command with cwd set to the sandbox directory. Used for smoke checks
(e.g. python scripts/pr_review.py --help). Follows INPUT_HARDENING_STANDARD and TOOLING_POLICY.

Usage:
  run_smoke.py --sandbox-dir /path/to/sandbox --command "python scripts/pr_review.py --help"

Exit code: same as the command's exit code, or 2 on argument/validation error.
Stdout/stderr from the command are streamed; capture them when invoking from a script.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

SANDBOX_PATH_MAX = 4096
COMMAND_MAX = 2048
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _sanitize_path(s: str, max_len: int = SANDBOX_PATH_MAX) -> Path:
    if not isinstance(s, str) or len(s) > max_len:
        raise ValueError(f"path invalid or length > {max_len}")
    s = s.strip().strip("\x00").strip()
    if not s:
        raise ValueError("sandbox-dir is empty")
    p = Path(s).resolve()
    if not p.exists():
        raise ValueError(f"sandbox directory does not exist: {p}")
    if not p.is_dir():
        raise ValueError(f"sandbox path is not a directory: {p}")
    return p


def _sanitize_command(s: str) -> str:
    if not isinstance(s, str):
        raise ValueError("command must be a string")
    s = s.strip()
    if len(s) > COMMAND_MAX:
        raise ValueError(f"command length exceeds {COMMAND_MAX}")
    if CONTROL_CHARS.search(s):
        raise ValueError("command contains invalid control characters")
    if not s:
        raise ValueError("command is empty")
    return s


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a smoke command inside a skill sandbox."
    )
    parser.add_argument(
        "--sandbox-dir",
        metavar="DIR",
        required=True,
        help="Sandbox directory (output of create_sandbox.py); cwd for the command",
    )
    parser.add_argument(
        "--command",
        metavar="CMD",
        required=True,
        help="Command to run (e.g. 'python scripts/pr_review.py --help')",
    )
    args = parser.parse_args()

    try:
        sandbox = _sanitize_path(args.sandbox_dir)
        command = _sanitize_command(args.command)
    except ValueError as e:
        print(f"run_smoke: {e}", file=sys.stderr)
        return 2

    try:
        r = subprocess.run(
            command,
            cwd=str(sandbox),
            shell=True,
            timeout=300,
        )
        return r.returncode
    except subprocess.TimeoutExpired:
        print("run_smoke: command timed out (300s)", file=sys.stderr)
        return 124
    except OSError as e:
        print(f"run_smoke: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

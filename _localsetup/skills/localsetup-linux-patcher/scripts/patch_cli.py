#!/usr/bin/env python3
# Purpose: CLI for Linux patcher (auto, host-only, host-full, multiple). Validates input and delegates to shell scripts.
# Created: 2026-02-20
# Last updated: 2026-02-20

"""
Patch CLI: run patch-auto, patch-host-only, patch-host-full, or patch-multiple with validated inputs.
Delegates to the corresponding .sh scripts. Requires ssh, and for auto mode: PatchMon credentials.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
HOST_MAX = 512
PATH_MAX = 4096


def _sanitize_host(s: str) -> str:
    if not isinstance(s, str) or len(s) > HOST_MAX:
        raise ValueError("host: invalid or too long")
    s = s.strip()
    if not s:
        raise ValueError("host: empty")
    if "\x00" in s or "\n" in s:
        raise ValueError("host: invalid characters")
    return s


def _sanitize_path(s: str) -> str:
    if not isinstance(s, str) or len(s) > PATH_MAX:
        raise ValueError("path: invalid or too long")
    s = s.strip()
    if "\x00" in s:
        raise ValueError("path: invalid characters")
    return s


def main() -> int:
    ap = argparse.ArgumentParser(description="Linux patcher: auto, host-only, host-full, multiple.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    auto = sub.add_parser("auto", help="Patch all hosts from PatchMon")
    auto.add_argument("--skip-docker", action="store_true", help="Skip Docker updates")
    auto.add_argument("--dry-run", action="store_true", help="Do not apply changes")
    ho = sub.add_parser("host-only", help="Update packages only on one host")
    ho.add_argument("host", help="user@hostname")
    hf = sub.add_parser("host-full", help="Update packages and Docker on one host")
    hf.add_argument("host", help="user@hostname")
    hf.add_argument("docker_path", help="Path to docker-compose on host")
    mult = sub.add_parser("multiple", help="Patch multiple hosts from config file")
    mult.add_argument("config", help="Path to config file")
    args = ap.parse_args()

    try:
        if args.cmd == "auto":
            cmd = [str(SCRIPT_DIR / "patch-auto.sh")]
            if args.skip_docker:
                cmd.append("--skip-docker")
            if args.dry_run:
                cmd.append("--dry-run")
        elif args.cmd == "host-only":
            _sanitize_host(args.host)
            cmd = [str(SCRIPT_DIR / "patch-host-only.sh"), args.host]
        elif args.cmd == "host-full":
            _sanitize_host(args.host)
            _sanitize_path(args.docker_path)
            cmd = [str(SCRIPT_DIR / "patch-host-full.sh"), args.host, args.docker_path]
        else:
            config = Path(args.config)
            if not config.is_file():
                print(f"Error: config file not found: {config}", file=sys.stderr)
                return 2
            cmd = [str(SCRIPT_DIR / "patch-multiple.sh"), str(config)]
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    r = subprocess.run(cmd)
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# Purpose: OS detection for framework tooling. Output: os_type|os_version|architecture.
# Created: 2026-02-20
# Last updated: 2026-02-20

import os
import platform
import subprocess
import sys
from pathlib import Path


def detect_os() -> str:
    """Return os_type|os_version|architecture (same contract as os_detector.sh)."""
    system = platform.system().lower()
    arch = platform.machine() or "unknown"
    version = "Unknown"

    if system == "linux":
        os_type = "linux"
        try:
            p = Path("/etc/os-release")
            if p.exists():
                text = p.read_text(encoding="utf-8", errors="replace")
                for line in text.splitlines():
                    if line.strip().startswith("PRETTY_NAME="):
                        version = line.split("=", 1)[1].strip().strip('"')
                        break
            if version == "Unknown":
                version = "Linux"
        except Exception:
            version = "Linux"
    elif system == "darwin":
        os_type = "macos"
        try:
            out = subprocess.run(
                ["sw_vers", "-productVersion"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if out.returncode == 0 and out.stdout.strip():
                version = out.stdout.strip()
        except Exception:
            pass
    elif system == "windows":
        os_type = "windows"
        version = "Windows"
        try:
            out = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "(Get-CimInstance Win32_OperatingSystem -ErrorAction SilentlyContinue).Caption",
                ],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if out.returncode == 0 and out.stdout.strip():
                version = out.stdout.strip()
        except Exception:
            pass
    else:
        os_type = "unknown"

    return f"{os_type}|{version}|{arch}"


if __name__ == "__main__":
    try:
        print(detect_os())
    except Exception as e:
        print(f"unknown|Unknown|{platform.machine()}", file=sys.stderr)
        sys.exit(1)

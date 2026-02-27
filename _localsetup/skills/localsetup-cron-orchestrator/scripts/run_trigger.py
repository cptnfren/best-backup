#!/usr/bin/env python3
# Purpose: Run all tasks for a named trigger in sequence (used by generated cron).
# Created: 2026-02-24
# Last updated: 2026-02-24

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import yaml

MAX_CMD_LEN = 8192
MAX_TRIGGER_LEN = 128


def _sanitize(s: str, max_len: int) -> str:
    if not isinstance(s, str):
        return ""
    out = "".join(c for c in s if ord(c) >= 0x20 and ord(c) != 0x7F)
    out = " ".join(out.split()).strip()
    return out[:max_len] if len(out) > max_len else out


def main() -> int:
    parser = argparse.ArgumentParser(description="Run tasks for a trigger in sequence.")
    parser.add_argument("--manifest", required=True, help="Path to manifest.yaml")
    parser.add_argument("--repo-root", help="Working directory for commands (default: manifest parent)")
    parser.add_argument("trigger", help="Trigger name")
    args = parser.parse_args()

    manifest_path = Path(args.manifest).resolve()
    if not manifest_path.is_file():
        print(f"[run_trigger] Not a file: {manifest_path}", file=sys.stderr)
        return 1
    repo_root = Path(args.repo_root).resolve() if args.repo_root else Path.cwd()
    if not repo_root.is_dir():
        print(f"[run_trigger] Not a directory: {repo_root}", file=sys.stderr)
        return 1

    trigger_name = _sanitize(args.trigger, MAX_TRIGGER_LEN)
    if not trigger_name:
        print("[run_trigger] Empty trigger name", file=sys.stderr)
        return 1

    try:
        raw = manifest_path.read_text(encoding="utf-8", errors="replace")
        data = yaml.safe_load(raw)
    except Exception as e:
        print(f"[run_trigger] Failed to load manifest: {e}", file=sys.stderr)
        return 1

    if not isinstance(data, dict):
        print("[run_trigger] Manifest root must be a dict", file=sys.stderr)
        return 1

    triggers = data.get("triggers") or {}
    if trigger_name not in triggers:
        print(f"[run_trigger] Unknown trigger: {trigger_name}", file=sys.stderr)
        return 1

    tasks = [t for t in (data.get("tasks") or []) if isinstance(t, dict)]
    tasks_for_trigger = [t for t in tasks if _sanitize(str(t.get("trigger", "")), MAX_TRIGGER_LEN) == trigger_name and t.get("enabled", True)]
    tasks_for_trigger.sort(key=lambda t: int(t.get("sequence_order", 0)))

    for task in tasks_for_trigger:
        cmd = (task.get("command") or "").strip()
        if len(cmd) > MAX_CMD_LEN:
            print(f"[run_trigger] Task {task.get('id', '?')}: command too long", file=sys.stderr)
            continue
        if not cmd:
            continue
        task_id = task.get("id", "?")
        try:
            r = subprocess.run(
                cmd,
                shell=True,
                cwd=repo_root,
                env={**os.environ, "LANG": "C"},
                timeout=3600,
            )
            if r.returncode != 0:
                print(f"[run_trigger] Task {task_id} exited {r.returncode}", file=sys.stderr)
                return r.returncode
        except subprocess.TimeoutExpired:
            print(f"[run_trigger] Task {task_id} timed out", file=sys.stderr)
            return 124
        except Exception as e:
            print(f"[run_trigger] Task {task_id}: {e}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

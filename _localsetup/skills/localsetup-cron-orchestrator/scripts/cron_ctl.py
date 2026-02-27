#!/usr/bin/env python3
# Purpose: Create, modify, remove, and install cron tasks from a manifest.
# Created: 2026-02-24
# Last updated: 2026-02-24

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

MANIFEST_DEFAULT = "cron/manifest.yaml"
MAX_ID_LEN = 128
MAX_TRIGGER_LEN = 128
MAX_CMD_LEN = 8192


def _sanitize(s: str, max_len: int) -> str:
    if not isinstance(s, str):
        return ""
    out = "".join(c for c in s if ord(c) >= 0x20 and ord(c) != 0x7F)
    out = " ".join(out.split()).strip()
    return out[:max_len] if len(out) > max_len else out


def _load_manifest(path: Path) -> tuple[dict, int]:
    if not path.is_file():
        print(f"[cron_ctl] Not a file: {path}", file=sys.stderr)
        return {}, 1
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
        data = yaml.safe_load(raw)
    except Exception as e:
        print(f"[cron_ctl] Failed to load manifest: {e}", file=sys.stderr)
        return {}, 1
    if not isinstance(data, dict):
        print("[cron_ctl] Manifest root must be a dict", file=sys.stderr)
        return {}, 1
    return data, 0


def _save_manifest(path: Path, data: dict) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    except Exception as e:
        print(f"[cron_ctl] Failed to write manifest: {e}", file=sys.stderr)
        return 1
    return 0


def cmd_validate(manifest_path: Path) -> int:
    data, code = _load_manifest(manifest_path)
    if code != 0:
        return code
    triggers = data.get("triggers") or {}
    tasks = [t for t in (data.get("tasks") or []) if isinstance(t, dict)]
    for t in tasks:
        tr = _sanitize(str(t.get("trigger", "")), MAX_TRIGGER_LEN)
        if tr and tr not in triggers:
            print(f"[cron_ctl] Task {t.get('id')} references unknown trigger: {tr}", file=sys.stderr)
            return 1
    print("OK")
    return 0


def cmd_list(manifest_path: Path, trigger_filter: str | None) -> int:
    data, code = _load_manifest(manifest_path)
    if code != 0:
        return code
    triggers = data.get("triggers") or {}
    tasks = [t for t in (data.get("tasks") or []) if isinstance(t, dict)]
    if trigger_filter:
        tasks = [t for t in tasks if _sanitize(str(t.get("trigger", "")), MAX_TRIGGER_LEN) == trigger_filter]
    tasks.sort(key=lambda t: (_sanitize(str(t.get("trigger", "")), MAX_TRIGGER_LEN), int(t.get("sequence_order", 0))))
    for t in tasks:
        tid = t.get("id", "?")
        tr = t.get("trigger", "?")
        order = t.get("sequence_order", 0)
        en = t.get("enabled", True)
        cmd = (t.get("command") or "")[:60] + ("..." if len(t.get("command") or "") > 60 else "")
        print(f"  {tid}  trigger={tr}  order={order}  enabled={en}  command={cmd}")
    return 0


def cmd_add_task(manifest_path: Path, trigger: str, command: str, sequence_order: int | None, task_id: str | None) -> int:
    data, code = _load_manifest(manifest_path)
    if code != 0:
        return code
    triggers = data.get("triggers") or {}
    tr = _sanitize(trigger, MAX_TRIGGER_LEN)
    if tr not in triggers:
        print(f"[cron_ctl] Unknown trigger: {tr}", file=sys.stderr)
        return 1
    tasks = data.get("tasks") or []
    existing_ids = {str(t.get("id", "")) for t in tasks if isinstance(t, dict)}
    if task_id:
        tid = _sanitize(task_id, MAX_ID_LEN)
        if tid in existing_ids:
            print(f"[cron_ctl] Task id already exists: {tid}", file=sys.stderr)
            return 1
    else:
        base = "task"
        n = 1
        while f"{base}-{n}" in existing_ids:
            n += 1
        tid = f"{base}-{n}"
    if sequence_order is None:
        same_trigger = [t for t in tasks if isinstance(t, dict) and _sanitize(str(t.get("trigger", "")), MAX_TRIGGER_LEN) == tr]
        sequence_order = max((int(t.get("sequence_order", 0)) for t in same_trigger), default=0) + 1
    cmd_san = _sanitize(command, MAX_CMD_LEN)
    tasks.append({"id": tid, "trigger": tr, "sequence_order": sequence_order, "command": cmd_san, "enabled": True})
    data["tasks"] = tasks
    return _save_manifest(manifest_path, data)


def cmd_remove_task(manifest_path: Path, task_id: str | None, trigger: str | None) -> int:
    if not task_id and not trigger:
        print("[cron_ctl] Specify --id ID or --trigger NAME", file=sys.stderr)
        return 1
    data, code = _load_manifest(manifest_path)
    if code != 0:
        return code
    tasks = [t for t in (data.get("tasks") or []) if isinstance(t, dict)]
    if task_id:
        tasks = [t for t in tasks if str(t.get("id", "")) != task_id]
        if len(tasks) == len(data.get("tasks") or []):
            print(f"[cron_ctl] No task with id: {task_id}", file=sys.stderr)
            return 1
    if trigger:
        tr = _sanitize(trigger, MAX_TRIGGER_LEN)
        tasks = [t for t in tasks if _sanitize(str(t.get("trigger", "")), MAX_TRIGGER_LEN) != tr]
    data["tasks"] = tasks
    return _save_manifest(manifest_path, data)


def cmd_reorder(manifest_path: Path, trigger: str, order_ids: list[str]) -> int:
    data, code = _load_manifest(manifest_path)
    if code != 0:
        return code
    tr = _sanitize(trigger, MAX_TRIGGER_LEN)
    tasks = list(data.get("tasks") or [])
    by_trigger = {t["id"]: t for t in tasks if isinstance(t, dict) and _sanitize(str(t.get("trigger", "")), MAX_TRIGGER_LEN) == tr}
    other = [t for t in tasks if isinstance(t, dict) and t.get("id") not in by_trigger]
    ordered = []
    for i, tid in enumerate(order_ids):
        if tid in by_trigger:
            by_trigger[tid]["sequence_order"] = i + 1
            ordered.append(by_trigger[tid])
    for t in by_trigger.values():
        if t not in ordered:
            ordered.append(t)
    ordered.sort(key=lambda t: int(t.get("sequence_order", 0)))
    data["tasks"] = other + ordered
    return _save_manifest(manifest_path, data)


def cmd_enable_disable(manifest_path: Path, task_id: str, enable: bool) -> int:
    data, code = _load_manifest(manifest_path)
    if code != 0:
        return code
    tasks = data.get("tasks") or []
    for t in tasks:
        if isinstance(t, dict) and str(t.get("id", "")) == task_id:
            t["enabled"] = enable
            return _save_manifest(manifest_path, data)
    print(f"[cron_ctl] No task with id: {task_id}", file=sys.stderr)
    return 1


def cmd_install(manifest_path: Path, repo_root: Path, output_path: Path | None, script_dir: Path) -> int:
    data, code = _load_manifest(manifest_path)
    if code != 0:
        return code
    repo_root = repo_root.resolve()
    run_trigger = (script_dir / "run_trigger.py").resolve()
    if not run_trigger.is_file():
        print(f"[cron_ctl] Runner not found: {run_trigger}", file=sys.stderr)
        return 1
    manifest_abs = manifest_path.resolve()
    lines = [
        "# Generated by cron_ctl install; merge with crontab -e or place in /etc/cron.d/",
        f"# Repo root: {repo_root}",
        f"# Manifest: {manifest_abs}",
        "",
    ]
    triggers = data.get("triggers") or {}
    tasks = [t for t in (data.get("tasks") or []) if isinstance(t, dict) and t.get("enabled", True)]
    for name, cfg in triggers.items():
        if not isinstance(cfg, dict):
            continue
        if "schedule" in cfg:
            cron_expr = _sanitize(str(cfg["schedule"]), 64)
            if cron_expr:
                lines.append(f"# Trigger: {name}")
                lines.append(f"{cron_expr}\tcd {repo_root} && python3 {run_trigger} --manifest {manifest_abs} --repo-root {repo_root} {name}")
                lines.append("")
        elif "on_boot_delay_minutes" in cfg:
            delay = max(0, int(cfg.get("on_boot_delay_minutes", 0)))
            lines.append(f"# Trigger: {name} (after boot, delay {delay} min)")
            lines.append(f"@reboot\tsleep {delay * 60} && cd {repo_root} && python3 {run_trigger} --manifest {manifest_abs} --repo-root {repo_root} {name}")
            lines.append("")
    out = "\n".join(lines)
    if output_path:
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(out, encoding="utf-8")
        print(f"Wrote {output_path}")
    else:
        print(out)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage cron tasks from a manifest.")
    parser.add_argument("--manifest", default=MANIFEST_DEFAULT, help="Path to manifest.yaml")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_validate = sub.add_parser("validate", help="Validate manifest")
    p_validate.set_defaults(fn=lambda a: cmd_validate(Path(a.manifest)))

    p_list = sub.add_parser("list", help="List tasks (optionally for one trigger)")
    p_list.add_argument("--trigger", help="Filter by trigger name")
    p_list.set_defaults(fn=lambda a: cmd_list(Path(a.manifest), getattr(a, "trigger", None)))

    p_add = sub.add_parser("add-task", help="Add a task")
    p_add.add_argument("--trigger", required=True)
    p_add.add_argument("--command", required=True)
    p_add.add_argument("--sequence-order", type=int, default=None)
    p_add.add_argument("--id", dest="task_id", default=None)
    p_add.set_defaults(fn=lambda a: cmd_add_task(Path(a.manifest), a.trigger, a.command, getattr(a, "sequence_order", None), getattr(a, "task_id", None)))

    p_remove = sub.add_parser("remove-task", help="Remove task(s)")
    p_remove.add_argument("--id", dest="task_id", default=None)
    p_remove.add_argument("--trigger", default=None, help="Remove all tasks for this trigger")
    p_remove.set_defaults(fn=lambda a: cmd_remove_task(Path(a.manifest), getattr(a, "task_id", None), getattr(a, "trigger", None)))

    p_reorder = sub.add_parser("reorder", help="Reorder tasks for a trigger")
    p_reorder.add_argument("--trigger", required=True)
    p_reorder.add_argument("--order", required=True, help="Comma-separated task ids in desired order")
    p_reorder.set_defaults(fn=lambda a: cmd_reorder(Path(a.manifest), a.trigger, [x.strip() for x in a.order.split(",")]))

    p_enable = sub.add_parser("enable", help="Enable a task")
    p_enable.add_argument("--id", dest="task_id", required=True)
    p_enable.set_defaults(fn=lambda a: cmd_enable_disable(Path(a.manifest), a.task_id, True))

    p_disable = sub.add_parser("disable", help="Disable a task")
    p_disable.add_argument("--id", dest="task_id", required=True)
    p_disable.set_defaults(fn=lambda a: cmd_enable_disable(Path(a.manifest), a.task_id, False))

    p_install = sub.add_parser("install", help="Generate crontab fragment")
    p_install.add_argument("--repo-root", default=".", help="Repo root (default: cwd)")
    p_install.add_argument("--output", default=None, help="Write to file (default: stdout)")
    p_install.set_defaults(fn=lambda a: cmd_install(Path(a.manifest), Path(a.repo_root), getattr(a, "output", None) and Path(a.output), Path(__file__).resolve().parent))

    args = parser.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())

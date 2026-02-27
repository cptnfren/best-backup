#!/usr/bin/env python3
# Purpose: Enable/disable/status tmux-default terminal mode (ide or shell layer + agent rule).
# Created: 2026-02-27
# Last Updated: 2026-02-27

"""
tmux_terminal_mode - Toggleable framework feature: tmux-default terminal mode.

Sub-commands:
  enable   Apply Layer 1 (ide or shell) + Layer 2 (agent rule).
  disable  Remove Layer 1 + Layer 2. Restore backups where available.
  status   Report which layers are active.

Run with --help for full flag reference.
"""

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TOOL_VERSION = "1.0.0"
SENTINEL_BEGIN = "# BEGIN tmux-default-terminal-mode"
SENTINEL_END   = "# END tmux-default-terminal-mode"
BAK_SUFFIX     = ".tmux-mode.bak"

DEFAULT_SESSION   = "ops"
DEFAULT_MODE      = "ide"
DEFAULT_RULES_FILE = ".cursor/rules/operator-memory.mdc"

# IDE settings.json search order (first existing path wins)
IDE_SETTINGS_CANDIDATES = [
    "~/.cursor-server/data/Machine/settings.json",
    "~/.vscode-server/data/Machine/settings.json",
    "~/Library/Application Support/Cursor/User/settings.json",
    "~/Library/Application Support/Code/User/settings.json",
]

# Agent rule block injected into the rules file (Layer 2)
# Kept in sync with localsetup-tmux-shared-session-workflow skill.
AGENT_RULE_BLOCK = """\
{sentinel_begin}
## MANDATORY: Server/ops (tmux + sudo gate)

Any request that involves running commands on the host uses the tmux workflow.
**Sudo is always assumed required.** Use the **tmux_ops** tool; do not infer
session from `tmux ls` or parse capture yourself.

1. **Session.** Run `./_localsetup/tools/tmux_ops pick`. Use the returned
   `session`. Right away, show the join command in a copy-paste code block:
   `tmux new-session -A -s <session>`. Do not wait for the user to confirm
   they joined. Then run the probe.

2. **Gate.** Run `./_localsetup/tools/tmux_ops probe -t <session>`. If
   `"sudo": "password_required"`: stop. Ask user to attach, enter password,
   reply "sudo ready". If `"sudo": "ready"`, proceed.

3. **Run.** One logical step per send; wait and verify before the next.
   Commands via `./_localsetup/tools/tmux_ops send -t <session> '<cmd>'`;
   capture to `/tmp/agent-<session>-*.log`; read the log. If sudo expires,
   probe again.

Full procedure: **localsetup-tmux-shared-session-workflow** skill.
{sentinel_end}
""".format(sentinel_begin=SENTINEL_BEGIN, sentinel_end=SENTINEL_END)

# Shell auto-attach block written to ~/.bashrc (Layer 1b)
SHELL_BLOCK_TEMPLATE = """\
{sentinel_begin}
# Auto-attach to tmux session if not already inside tmux.
# Applies to interactive non-tmux shells only (SSH, local terminal, etc).
if [ -z "$TMUX" ] && [ -n "$PS1" ]; then
  exec tmux new-session -A -s {session}
fi
{sentinel_end}
"""


# ---------------------------------------------------------------------------
# Errors and I/O helpers
# ---------------------------------------------------------------------------

def _die(msg: str, code: int = 1) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)
    sys.exit(code)


def _warn(msg: str) -> None:
    print(f"[WARN]  {msg}", file=sys.stderr)


def _info(msg: str) -> None:
    print(f"[INFO]  {msg}")


def _ok(msg: str) -> None:
    print(f"[OK]    {msg}")


def _dry(msg: str) -> None:
    print(f"[DRY]   {msg}")


# ---------------------------------------------------------------------------
# Sentinel helpers
# ---------------------------------------------------------------------------

def _has_sentinel(text: str) -> bool:
    return SENTINEL_BEGIN in text


def _strip_sentinel_block(text: str) -> str:
    """Remove everything between (and including) the sentinel lines."""
    pattern = re.compile(
        r"\n?" + re.escape(SENTINEL_BEGIN) + r".*?" + re.escape(SENTINEL_END) + r"\n?",
        re.DOTALL,
    )
    return pattern.sub("", text)


# ---------------------------------------------------------------------------
# Atomic file write
# ---------------------------------------------------------------------------

def _atomic_write(path: Path, content: str) -> None:
    """Write content atomically: write to .tmp then rename."""
    try:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(path)
    except OSError as exc:
        _die(f"Failed to write {path}: {exc}")


# ---------------------------------------------------------------------------
# Backup helpers
# ---------------------------------------------------------------------------

def _backup(path: Path, dry_run: bool) -> Path:
    """Create a .tmux-mode.bak copy if not already present. Returns backup path."""
    bak = path.with_suffix(path.suffix + BAK_SUFFIX)
    if bak.exists():
        return bak
    if dry_run:
        _dry(f"Would back up {path} → {bak}")
        return bak
    try:
        shutil.copy2(str(path), str(bak))
        _info(f"Backed up {path} → {bak}")
    except OSError as exc:
        _die(f"Could not back up {path}: {exc}")
    return bak


def _restore_or_strip(path: Path, dry_run: bool, label: str) -> None:
    """Restore from backup if present; otherwise strip the sentinel block."""
    bak = path.with_suffix(path.suffix + BAK_SUFFIX)
    if bak.exists():
        if dry_run:
            _dry(f"Would restore {label} from backup: {bak} → {path}")
        else:
            try:
                shutil.copy2(str(bak), str(path))
                bak.unlink()
                _ok(f"Restored {label} from backup: {path}")
            except OSError as exc:
                _die(f"Could not restore {path} from backup: {exc}")
        return

    if not path.exists():
        _info(f"Nothing to do for {label} ({path} not found).")
        return

    text = _safe_read(path)
    if not _has_sentinel(text):
        _info(f"Nothing to do for {label} (no sentinel block found in {path}).")
        return

    stripped = _strip_sentinel_block(text)
    if dry_run:
        _dry(f"Would remove sentinel block from {label}: {path}")
    else:
        _atomic_write(path, stripped)
        _ok(f"Removed sentinel block from {label}: {path}")


def _safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        _die(f"Cannot read {path}: {exc}")


# ---------------------------------------------------------------------------
# tmux path resolution
# ---------------------------------------------------------------------------

def _resolve_tmux() -> str:
    result = shutil.which("tmux")
    if not result:
        _die(
            "tmux not found in PATH.\n"
            "  Install tmux (e.g. sudo apt install tmux) and try again."
        )
    return result


# ---------------------------------------------------------------------------
# IDE settings.json helpers (Layer 1a)
# ---------------------------------------------------------------------------

def _detect_settings_file() -> Optional[Path]:
    """
    Return an IDE settings file path, creating it (as empty JSON) if the parent
    directory exists but the file does not. Returns None only when no candidate
    parent directory is found at all.
    """
    for candidate in IDE_SETTINGS_CANDIDATES:
        p = Path(candidate).expanduser()
        if p.exists():
            return p
        if p.parent.exists():
            # Parent dir is present (Cursor/VS Code is installed); bootstrap the file.
            try:
                p.write_text("{}\n", encoding="utf-8")
                _info(f"Created empty settings file: {p}")
            except OSError as exc:
                _warn(f"Could not create {p}: {exc}; trying next candidate.")
                continue
            return p
    return None


def _load_json_settings(path: Path) -> dict:
    if not path.exists():
        return {}
    text = _safe_read(path)
    if not text.strip():
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        _die(
            f"settings.json at {path} is not valid JSON: {exc}\n"
            "  Fix the file manually or use --settings-file to point to a different path."
        )


def _write_json_settings(path: Path, data: dict, dry_run: bool) -> None:
    content = json.dumps(data, indent=4) + "\n"
    if dry_run:
        _dry(f"Would write IDE settings to {path}")
    else:
        _atomic_write(path, content)
        _ok(f"Wrote IDE settings: {path}")


def _apply_ide_layer(settings_path: Path, session: str, tmux_path: str, dry_run: bool) -> None:
    _backup(settings_path, dry_run)
    data = _load_json_settings(settings_path)

    profiles_key   = "terminal.integrated.profiles.linux"
    default_key    = "terminal.integrated.defaultProfile.linux"
    profile_name   = "tmux-session"

    profiles = data.get(profiles_key, {})
    profiles[profile_name] = {
        "path": tmux_path,
        "args": ["new-session", "-A", "-s", session],
        "icon": "terminal-tmux",
    }
    data[profiles_key] = profiles
    data[default_key]  = profile_name

    _write_json_settings(settings_path, data, dry_run)
    if not dry_run:
        _ok(f"Layer 1a (IDE profile): tmux-session → {session}")


def _remove_ide_layer(settings_path: Path, dry_run: bool) -> None:
    bak = settings_path.with_suffix(settings_path.suffix + BAK_SUFFIX)
    if bak.exists():
        if dry_run:
            _dry(f"Would restore IDE settings from backup: {bak} → {settings_path}")
        else:
            shutil.copy2(str(bak), str(settings_path))
            bak.unlink()
            _ok(f"Restored IDE settings from backup: {settings_path}")
        return

    if not settings_path.exists():
        _info("Nothing to do for Layer 1a (settings file not found).")
        return

    data = _load_json_settings(settings_path)
    profiles_key = "terminal.integrated.profiles.linux"
    default_key  = "terminal.integrated.defaultProfile.linux"
    profile_name = "tmux-session"

    changed = False
    profiles = data.get(profiles_key, {})
    if profile_name in profiles:
        del profiles[profile_name]
        data[profiles_key] = profiles
        changed = True
    if default_key in data:
        del data[default_key]
        changed = True

    if not changed:
        _info("Nothing to do for Layer 1a (profile not found in settings).")
        return

    _write_json_settings(settings_path, data, dry_run)


def _ide_layer_active(settings_path: Optional[Path]) -> Optional[str]:
    """Return session name if IDE profile is active, else None."""
    if not settings_path or not settings_path.exists():
        return None
    data = _load_json_settings(settings_path)
    profiles = data.get("terminal.integrated.profiles.linux", {})
    profile  = profiles.get("tmux-session", {})
    args     = profile.get("args", [])
    if len(args) >= 3 and args[0] == "new-session" and args[1] == "-A" and args[2] == "-s":
        return args[3] if len(args) > 3 else DEFAULT_SESSION
    return None


# ---------------------------------------------------------------------------
# Shell RC helpers (Layer 1b)
# ---------------------------------------------------------------------------

def _default_shell_rc() -> Path:
    if platform.system() == "Darwin":
        p = Path("~/.bash_profile").expanduser()
        if p.exists():
            return p
    return Path("~/.bashrc").expanduser()


def _apply_shell_layer(rc_path: Path, session: str, dry_run: bool) -> None:
    if not rc_path.exists():
        if dry_run:
            _dry(f"Would create {rc_path} and append shell auto-attach block")
            return
        rc_path.parent.mkdir(parents=True, exist_ok=True)
        rc_path.write_text("", encoding="utf-8")
        _info(f"Created {rc_path}")
    else:
        _backup(rc_path, dry_run)

    if dry_run:
        text = _safe_read(rc_path)
        if _has_sentinel(text):
            _info(f"Layer 1b already present in {rc_path} (idempotent, no change).")
        else:
            _dry(f"Would append shell auto-attach block to {rc_path}")
        return

    text = _safe_read(rc_path)
    if _has_sentinel(text):
        _info(f"Layer 1b already present in {rc_path} (idempotent, no change).")
        return

    block = SHELL_BLOCK_TEMPLATE.format(
        sentinel_begin=SENTINEL_BEGIN,
        sentinel_end=SENTINEL_END,
        session=session,
    )
    if dry_run:
        _dry(f"Would append shell auto-attach block to {rc_path}")
    else:
        with open(rc_path, "a", encoding="utf-8") as f:
            f.write("\n" + block)
        _ok(f"Layer 1b (shell auto-attach): appended to {rc_path}")


def _remove_shell_layer(rc_path: Path, dry_run: bool) -> None:
    _restore_or_strip(rc_path, dry_run, "Layer 1b (shell RC)")


def _shell_layer_active(rc_path: Path) -> Optional[str]:
    """Return session name from sentinel block if present, else None."""
    if not rc_path.exists():
        return None
    text = _safe_read(rc_path)
    if not _has_sentinel(text):
        return None
    m = re.search(r"exec tmux new-session -A -s (\S+)", text)
    return m.group(1) if m else DEFAULT_SESSION


# ---------------------------------------------------------------------------
# Agent rule helpers (Layer 2)
# ---------------------------------------------------------------------------

def _apply_rule_layer(rules_path: Path, dry_run: bool) -> None:
    rules_path.parent.mkdir(parents=True, exist_ok=True)
    if not rules_path.exists():
        if dry_run:
            _dry(f"Would create {rules_path} and append agent rule block")
            return
        rules_path.write_text("", encoding="utf-8")
        _info(f"Created {rules_path}")
    else:
        _backup(rules_path, dry_run)

    if dry_run:
        text = _safe_read(rules_path)
        if _has_sentinel(text):
            _info(f"Layer 2 already present in {rules_path} (idempotent, no change).")
        else:
            _dry(f"Would append agent rule block to {rules_path}")
        return

    text = _safe_read(rules_path)
    if _has_sentinel(text):
        _info(f"Layer 2 already present in {rules_path} (idempotent, no change).")
        return

    with open(rules_path, "a", encoding="utf-8") as f:
        f.write("\n" + AGENT_RULE_BLOCK)
    _ok(f"Layer 2 (agent rule): appended to {rules_path}")


def _remove_rule_layer(rules_path: Path, dry_run: bool) -> None:
    _restore_or_strip(rules_path, dry_run, "Layer 2 (agent rule)")


def _rule_layer_active(rules_path: Path) -> bool:
    if not rules_path.exists():
        return False
    return _has_sentinel(_safe_read(rules_path))


# ---------------------------------------------------------------------------
# tmux_ops tool check (Layer 3)
# ---------------------------------------------------------------------------

def _tmux_ops_path() -> Optional[Path]:
    here = Path(__file__).resolve().parent
    p = here / "tmux_ops"
    return p if p.exists() else None


# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------

def cmd_enable(args: argparse.Namespace) -> int:
    mode        = args.mode
    session     = args.session
    dry_run     = args.dry_run
    rules_path  = Path(args.rules_file).expanduser()

    tmux_path = _resolve_tmux()
    _info(f"tmux: {tmux_path}")

    if mode == "ide":
        if args.settings_file:
            settings_path = Path(args.settings_file).expanduser()
            if not settings_path.exists():
                if settings_path.parent.exists():
                    try:
                        settings_path.write_text("{}\n", encoding="utf-8")
                        _info(f"Created empty settings file: {settings_path}")
                    except OSError as exc:
                        _die(f"Could not create {settings_path}: {exc}")
                else:
                    _die(
                        f"--settings-file {settings_path} does not exist and its parent "
                        f"directory does not exist either.\n"
                        "  Create the directory first or use --mode shell."
                    )
        else:
            settings_path = _detect_settings_file()
            if not settings_path:
                _die(
                    "No IDE settings directory detected. Checked:\n"
                    + "\n".join(f"  {c}" for c in IDE_SETTINGS_CANDIDATES)
                    + "\n\nNone of the expected parent directories exist on this machine.\n"
                    "Use --settings-file <path> to specify one, or use --mode shell."
                )

        _info(f"Mode: ide  |  settings: {settings_path}  |  session: {session}")
        _apply_ide_layer(settings_path, session, tmux_path, dry_run)

    elif mode == "shell":
        rc_path = Path(args.shell_rc).expanduser() if args.shell_rc else _default_shell_rc()
        _info(f"Mode: shell  |  rc: {rc_path}  |  session: {session}")
        _apply_shell_layer(rc_path, session, dry_run)

    _apply_rule_layer(rules_path, dry_run)

    if not dry_run:
        print()
        _ok("tmux-default terminal mode enabled.")
        if mode == "ide":
            print("  Restart the IDE terminal panel for the new profile to appear.")
        elif mode == "shell":
            print("  Open a new shell session to activate auto-attach.")
            print("  NOTE: shell mode uses 'exec tmux', so a new terminal is the only")
            print("  clean way back to a plain shell after disabling.")
    else:
        print()
        _dry("Dry-run complete. No files were modified.")

    return 0


def cmd_disable(args: argparse.Namespace) -> int:
    mode       = args.mode
    dry_run    = args.dry_run
    rules_path = Path(args.rules_file).expanduser()

    anything_done = False

    if mode == "ide":
        if args.settings_file:
            settings_path = Path(args.settings_file).expanduser()
        else:
            settings_path = _detect_settings_file()
            # Also check if a backup exists even if the live file is missing
            if not settings_path:
                for c in IDE_SETTINGS_CANDIDATES:
                    p = Path(c).expanduser()
                    bak = p.with_suffix(p.suffix + BAK_SUFFIX)
                    if bak.exists():
                        settings_path = p
                        break

        if settings_path:
            bak = settings_path.with_suffix(settings_path.suffix + BAK_SUFFIX)
            was_active = _ide_layer_active(settings_path) is not None or bak.exists()
            _remove_ide_layer(settings_path, dry_run)
            if was_active:
                anything_done = True
        else:
            _info("Nothing to do for Layer 1a (no IDE settings file found).")

    elif mode == "shell":
        rc_path = Path(args.shell_rc).expanduser() if args.shell_rc else _default_shell_rc()
        was_active = _shell_layer_active(rc_path) is not None
        _remove_shell_layer(rc_path, dry_run)
        if was_active:
            anything_done = True

    rule_was_active = _rule_layer_active(rules_path)
    _remove_rule_layer(rules_path, dry_run)
    if rule_was_active:
        anything_done = True

    if not anything_done:
        print()
        _info("Nothing to do. tmux-default terminal mode was not enabled.")
        return 0

    if not dry_run:
        print()
        _ok("tmux-default terminal mode disabled.")
        if mode == "ide":
            print("  Restart the IDE terminal panel to return to the default shell.")
        elif mode == "shell":
            print("  Open a new shell session to get a plain shell.")
    else:
        print()
        _dry("Dry-run complete. No files were modified.")

    return 0


def cmd_status(args: argparse.Namespace) -> int:
    rules_path = Path(args.rules_file).expanduser()

    # Detect settings path regardless of --mode
    if args.settings_file:
        settings_path = Path(args.settings_file).expanduser()
    else:
        settings_path = _detect_settings_file()

    # Detect shell RC regardless of --mode
    if args.shell_rc:
        rc_path = Path(args.shell_rc).expanduser()
    else:
        rc_path = _default_shell_rc()

    ide_session   = _ide_layer_active(settings_path)
    shell_session = _shell_layer_active(rc_path)
    rule_active   = _rule_layer_active(rules_path)
    tmux_ops      = _tmux_ops_path()

    # Infer detected mode
    if ide_session:
        detected_mode = "ide"
        detected_session = ide_session
    elif shell_session:
        detected_mode = "shell"
        detected_session = shell_session
    else:
        detected_mode = "none"
        detected_session = "-"

    print()
    print("tmux-default terminal mode status")
    print(f"  Mode detected:           {detected_mode}")
    print(f"  Session name:            {detected_session}")

    # Layer 1a
    if ide_session:
        settings_label = str(settings_path) if settings_path else "unknown"
        print(f"  Layer 1a (IDE profile):  ACTIVE   [tmux-session → {ide_session}, settings: {settings_label}]")
    else:
        print(f"  Layer 1a (IDE profile):  INACTIVE")

    # Layer 1b
    if shell_session:
        print(f"  Layer 1b (shell RC):     ACTIVE   [session: {shell_session}, rc: {rc_path}]")
    else:
        print(f"  Layer 1b (shell RC):     INACTIVE")

    # Layer 2
    if rule_active:
        print(f"  Layer 2  (agent rule):   ACTIVE   [rules: {rules_path}]")
    else:
        print(f"  Layer 2  (agent rule):   INACTIVE")

    # Layer 3
    if tmux_ops:
        print(f"  Layer 3  (tmux_ops):     PRESENT  [{tmux_ops}]")
    else:
        print(f"  Layer 3  (tmux_ops):     MISSING  (expected at _localsetup/tools/tmux_ops)")

    print()
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tmux_terminal_mode",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {TOOL_VERSION}")

    sub = p.add_subparsers(dest="subcommand", metavar="SUBCOMMAND")
    sub.required = True

    # Shared flags factory
    def _add_common(sp):
        sp.add_argument("--mode", choices=["ide", "shell"], default=DEFAULT_MODE,
                        help=f"Layer 1 variant (default: {DEFAULT_MODE})")
        sp.add_argument("--session", default=DEFAULT_SESSION, metavar="NAME",
                        help=f"tmux session name (default: {DEFAULT_SESSION})")
        sp.add_argument("--settings-file", metavar="PATH",
                        help="IDE settings.json path (ide mode; auto-detected if omitted)")
        sp.add_argument("--shell-rc", metavar="PATH",
                        help="Shell RC file path (shell mode; default: ~/.bashrc or ~/.bash_profile on macOS)")
        sp.add_argument("--rules-file", default=DEFAULT_RULES_FILE, metavar="PATH",
                        help=f"Agent rules file (default: {DEFAULT_RULES_FILE})")
        sp.add_argument("--dry-run", action="store_true",
                        help="Print planned changes without modifying any file")

    en = sub.add_parser("enable", help="Apply tmux-default terminal mode")
    _add_common(en)
    en.set_defaults(func=cmd_enable)

    dis = sub.add_parser("disable", help="Remove tmux-default terminal mode")
    _add_common(dis)
    dis.set_defaults(func=cmd_disable)

    st = sub.add_parser("status", help="Report which layers are active")
    st.add_argument("--settings-file", metavar="PATH",
                    help="IDE settings.json path (auto-detected if omitted)")
    st.add_argument("--shell-rc", metavar="PATH",
                    help="Shell RC file path (default: ~/.bashrc or ~/.bash_profile on macOS)")
    st.add_argument("--rules-file", default=DEFAULT_RULES_FILE, metavar="PATH",
                    help=f"Agent rules file (default: {DEFAULT_RULES_FILE})")
    st.set_defaults(func=cmd_status)

    return p


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

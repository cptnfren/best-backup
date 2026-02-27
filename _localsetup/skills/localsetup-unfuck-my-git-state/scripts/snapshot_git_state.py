#!/usr/bin/env python3
# Purpose: Capture Git repo state to a timestamped directory for diagnosis. Replaces snapshot_git_state.sh.
# Created: 2026-02-20
# Last updated: 2026-02-20

"""
Capture Git work tree state to .git-state-snapshots/<stamp>/ for safe diagnosis.
Usage: snapshot_git_state.py [REPO_PATH]
REPO_PATH defaults to current directory. Must be inside a Git work tree.
"""

import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PATH_MAX = 4096
REPO_ARG_MAX = 1024


def _sanitize_path(s: str) -> Path:
    if not isinstance(s, str) or len(s) > REPO_ARG_MAX:
        raise ValueError(f"repo path: invalid length or type (max {REPO_ARG_MAX})")
    s = s.strip().strip("\x00")
    if not s:
        s = "."
    p = Path(s).resolve()
    if not p.exists():
        raise ValueError(f"repo path does not exist: {p}")
    if not p.is_dir():
        raise ValueError(f"repo path is not a directory: {p}")
    return p


def _run_git(repo: Path, *args: str) -> str:
    cmd = ["git", "-C", str(repo)] + list(args)
    r = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return r.stdout or "" if r.returncode == 0 else ""


def _run_capture(repo: Path, out_dir: Path, name: str, *git_args: str) -> None:
    cmd = ["git", "-C", str(repo)] + list(git_args)
    out_file = out_dir / f"{name}.txt"
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        content = f"# {name}\n# command: {' '.join(cmd)}\n\n"
        content += r.stdout or ""
        if r.stderr:
            content += r.stderr
        out_file.write_text(content, encoding="utf-8", errors="replace")
    except Exception as e:
        out_file.write_text(
            f"# {name}\n# command: {' '.join(cmd)}\n# error: {e}\n",
            encoding="utf-8",
            errors="replace",
        )


def main() -> int:
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__.strip())
        return 0
    repo_raw = sys.argv[1] if len(sys.argv) > 1 else "."
    try:
        repo = _sanitize_path(repo_raw)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    try:
        r = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode != 0:
            print(f"Error: '{repo}' is not inside a Git work tree", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    toplevel = _run_git(repo, "rev-parse", "--show-toplevel").strip()
    if not toplevel:
        print("Error: could not get Git toplevel", file=sys.stderr)
        return 2
    toplevel = str(Path(toplevel).resolve())
    git_dir = _run_git(repo, "rev-parse", "--git-dir").strip()
    if not git_dir:
        print("Error: could not get Git dir", file=sys.stderr)
        return 2
    git_dir_abs = Path(git_dir) if Path(git_dir).is_absolute() else Path(toplevel) / git_dir

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_dir = Path(toplevel) / ".git-state-snapshots" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "context.txt").write_text(
        f"snapshot_time={stamp}\ntarget={repo}\ntoplevel={toplevel}\ngit_dir={git_dir_abs}\n"
        f"git_version={_run_git(repo, '--version').strip()}\n",
        encoding="utf-8",
        errors="replace",
    )

    if (git_dir_abs / "HEAD").is_file():
        (out_dir / "head-file.txt").write_text(
            (git_dir_abs / "HEAD").read_text(encoding="utf-8", errors="replace"),
            encoding="utf-8",
            errors="replace",
        )
    if (git_dir_abs / "worktrees").is_dir():
        r = subprocess.run(
            ["ls", "-la", str(git_dir_abs / "worktrees")],
            capture_output=True,
            text=True,
            timeout=5,
        )
        (out_dir / "worktrees-dir-listing.txt").write_text(
            r.stdout or r.stderr or "",
            encoding="utf-8",
            errors="replace",
        )

    _run_capture(repo, out_dir, "status", "status", "--porcelain=v2", "--branch")
    _run_capture(repo, out_dir, "branch_current", "branch", "--show-current")
    _run_capture(repo, out_dir, "symbolic_ref_head", "symbolic-ref", "-q", "HEAD")
    _run_capture(repo, out_dir, "worktree_list", "worktree", "list", "--porcelain")
    _run_capture(repo, out_dir, "branch_all_verbose", "branch", "-vv", "--all")
    _run_capture(repo, out_dir, "remote_verbose", "remote", "-v")
    _run_capture(repo, out_dir, "show_ref", "show-ref", "--head")
    _run_capture(repo, out_dir, "reflog_head", "reflog", "--date=iso", "-n", "50", "HEAD")
    _run_capture(repo, out_dir, "fsck", "fsck", "--full", "--no-reflogs")

    print("Git state snapshot captured.")
    print(f"Directory: {out_dir}")
    print("Use these files to diagnose before changing refs or worktrees.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

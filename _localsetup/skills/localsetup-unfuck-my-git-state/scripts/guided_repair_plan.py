#!/usr/bin/env python3
# Purpose: Print non-destructive Git recovery plans by symptom or snapshot. Replaces guided_repair_plan.sh.
# Created: 2026-02-20
# Last updated: 2026-02-20

"""
Print recommended Git recovery steps. Does not run fix commands.
Usage: guided_repair_plan.py --list | --symptom <key> | --repo <path> | --snapshot <path>
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PATH_MAX = 4096
SYMPTOM_MAX = 64

SYMPTOMS = [
    "orphaned-worktree-metadata",
    "phantom-branch-lock",
    "detached-head-state",
    "head-ref-disagreement",
    "missing-or-broken-refs",
    "zero-hash-worktree-entry",
]

PLANS = {
    "orphaned-worktree-metadata": """[orphaned-worktree-metadata]
Run these first:
  git worktree list --porcelain
  git worktree prune -v
  git worktree list --porcelain

If stale entries still exist, back up `.git/` and then remove only the stale
`.git/worktrees/<name>` directory before rerunning prune.""",
    "phantom-branch-lock": """[phantom-branch-lock]
Run these first:
  git worktree list --porcelain

Then:
  1) Identify the worktree currently owning the branch.
  2) In that worktree, switch to another branch (or intentionally detach HEAD).
  3) Retry branch delete/switch in your main repo.

If ownership metadata is stale after verification, back up `.git/` before manual cleanup.""",
    "detached-head-state": """[detached-head-state]
Run these first:
  git symbolic-ref -q HEAD || true
  git reflog --date=iso -n 20
  git switch <known-good-branch>

If branch context is unknown:
  git switch -c rescue/$(date +%Y%m%d-%H%M%S)""",
    "head-ref-disagreement": """[head-ref-disagreement]
Run these first:
  git branch --show-current
  git symbolic-ref -q HEAD
  git show-ref --verify refs/heads/<expected-branch>
  git symbolic-ref HEAD refs/heads/<expected-branch>

Fallback only after backup:
  echo "ref: refs/heads/<expected-branch>" > .git/HEAD""",
    "missing-or-broken-refs": """[missing-or-broken-refs]
Run these first:
  git fetch --all --prune
  git show-ref --verify refs/remotes/origin/<branch>
  git branch -f <branch> origin/<branch>
  git switch <branch>

Before forcing branch pointers, inspect reflog for local-only commits:
  git reflog --date=iso -n 50 HEAD""",
    "zero-hash-worktree-entry": """[zero-hash-worktree-entry]
Run these first:
  git worktree list --porcelain
  git worktree prune -v
  git worktree list --porcelain

If zero-hash entries persist, recreate affected worktree(s) from a verified branch ref.""",
}


def _sanitize(s: str, max_len: int, name: str) -> str:
    if not isinstance(s, str) or len(s) > max_len:
        raise ValueError(f"{name}: invalid length or type (max {max_len})")
    s = " ".join(s.split()).strip()
    return s


def _sanitize_path(s: str) -> Path:
    s = _sanitize(s, PATH_MAX, "path")
    p = Path(s).resolve()
    if not p.exists() or not p.is_dir():
        raise ValueError(f"path does not exist or is not a directory: {p}")
    return p


def list_symptoms() -> None:
    print("Available symptom keys:")
    for s in SYMPTOMS:
        print(f"  {s}")


def print_plan(symptom: str) -> None:
    if symptom not in PLANS:
        print(f"Error: unknown symptom '{symptom}'", file=sys.stderr)
        sys.exit(1)
    print(PLANS[symptom])


def _last_line_no_comment(path: Path) -> str:
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    for line in reversed(text.splitlines()):
        line = line.strip()
        if line and not line.startswith("#"):
            return line
    return ""


def run_detection(snapshot_dir: Path) -> None:
    worktree_file = snapshot_dir / "worktree_list.txt"
    status_file = snapshot_dir / "status.txt"
    branch_file = snapshot_dir / "branch_current.txt"
    symbolic_file = snapshot_dir / "symbolic_ref_head.txt"
    show_ref_file = snapshot_dir / "show_ref.txt"

    matches = []

    if worktree_file.is_file():
        content = worktree_file.read_text(encoding="utf-8", errors="replace")
        for line in content.splitlines():
            if line.startswith("worktree "):
                wt_path = line[9:].strip()
                if wt_path and not Path(wt_path).exists():
                    matches.append("orphaned-worktree-metadata")
                    break

        content = worktree_file.read_text(encoding="utf-8", errors="replace")
        if re.search(r"^HEAD\s+0{40}", content, re.MULTILINE):
            if status_file.is_file():
                st = status_file.read_text(encoding="utf-8", errors="replace")
                if re.search(r"No commits yet|branch\.oid\s+\(initial\)", st):
                    pass
                else:
                    matches.append("zero-hash-worktree-entry")
            else:
                matches.append("zero-hash-worktree-entry")

    if status_file.is_file():
        st = status_file.read_text(encoding="utf-8", errors="replace")
        if re.search(r"detached|HEAD detached", st, re.IGNORECASE):
            matches.append("detached-head-state")

    cur_branch = _last_line_no_comment(branch_file)
    sym_branch = _last_line_no_comment(symbolic_file).replace("refs/heads/", "")
    if cur_branch and sym_branch and cur_branch != sym_branch:
        matches.append("head-ref-disagreement")

    if status_file.is_file():
        st = status_file.read_text(encoding="utf-8", errors="replace")
        if re.search(r"unknown revision|not a valid object name|cannot lock ref|fatal:", st, re.IGNORECASE):
            matches.append("missing-or-broken-refs")
    if show_ref_file.is_file():
        sr = show_ref_file.read_text(encoding="utf-8", errors="replace")
        if re.search(r"not a valid|fatal:", sr, re.IGNORECASE):
            matches.append("missing-or-broken-refs")

    unique = list(dict.fromkeys(matches))
    if not unique:
        print(f"No deterministic symptom match found in snapshot: {snapshot_dir}", file=sys.stderr)
        print("Use --symptom with one of:", file=sys.stderr)
        list_symptoms()
        return
    print(f"Detected symptom(s) from snapshot: {snapshot_dir}", file=sys.stderr)
    for s in unique:
        print()
        print_plan(s)


def resolve_snapshot_from_repo(repo: Path) -> Path:
    r = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "snapshot_git_state.py"), str(repo)],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(SCRIPT_DIR),
    )
    if r.stderr:
        print(r.stderr, file=sys.stderr)
    for line in (r.stdout or "").splitlines():
        if line.startswith("Directory: "):
            d = line[11:].strip()
            if d:
                p = Path(d)
                if p.is_dir():
                    return p
    top = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    if top.returncode != 0:
        print(f"Error: unable to resolve snapshot directory for repo '{repo}'", file=sys.stderr)
        sys.exit(1)
    top_path = Path(top.stdout.strip())
    snap_dir = top_path / ".git-state-snapshots"
    if not snap_dir.is_dir():
        print(f"Error: no snapshot directory for repo '{repo}'", file=sys.stderr)
        sys.exit(1)
    latest = sorted(snap_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    if not latest:
        print(f"Error: no snapshots in {snap_dir}", file=sys.stderr)
        sys.exit(1)
    return latest[0]


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Print non-destructive Git recovery plans by symptom or snapshot.",
    )
    ap.add_argument("--list", "-l", action="store_true", help="List symptom keys")
    ap.add_argument("--symptom", metavar="KEY", help="Print plan for symptom key")
    ap.add_argument("--repo", metavar="PATH", help="Repo path; take or use latest snapshot")
    ap.add_argument("--snapshot", metavar="PATH", help="Path to snapshot directory")
    args = ap.parse_args()

    if args.list:
        list_symptoms()
        return 0

    if args.symptom:
        try:
            key = _sanitize(args.symptom, SYMPTOM_MAX, "symptom")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 2
        print_plan(key)
        return 0

    if not args.snapshot and not args.repo:
        print("Error: provide --symptom, --snapshot, or --repo", file=sys.stderr)
        ap.print_help(file=sys.stderr)
        return 2

    snapshot = args.snapshot
    if not snapshot and args.repo:
        try:
            repo = _sanitize_path(args.repo)
            snapshot_dir = resolve_snapshot_from_repo(repo)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 2
    else:
        try:
            snapshot_dir = _sanitize_path(snapshot)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 2

    if not snapshot_dir.is_dir():
        print(f"Error: snapshot directory not found: {snapshot_dir}", file=sys.stderr)
        return 1
    run_detection(snapshot_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())

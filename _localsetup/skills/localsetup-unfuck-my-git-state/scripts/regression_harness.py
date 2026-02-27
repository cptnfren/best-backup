#!/usr/bin/env python3
# Purpose: Disposable Git state regression scenarios. Replaces regression_harness.sh.
# Created: 2026-02-20
# Last updated: 2026-02-20

"""
Run regression scenarios that verify guided_repair_plan detection.
Usage: regression_harness.py [--scenario NAME] [--list] [--keep-temp]
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
GUIDED_SCRIPT = SCRIPT_DIR / "guided_repair_plan.py"
SCENARIOS = [
    "orphaned-worktree",
    "detached-head",
    "zero-hash-worktree",
    "manual-phantom-branch-lock",
]
NAME_MAX = 64


def _sanitize(s: str) -> str:
    if not isinstance(s, str) or len(s) > NAME_MAX:
        raise ValueError(f"scenario name invalid (max {NAME_MAX})")
    s = " ".join(s.split()).strip()
    if not s:
        raise ValueError("scenario name empty")
    return s


def run_cmd(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        list(args),
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=60,
    )


def make_repo(work_root: Path, name: str) -> Path:
    repo = work_root / name
    repo.mkdir(parents=True, exist_ok=True)
    run_cmd(repo, "git", "init", "-q")
    run_cmd(repo, "git", "config", "user.name", "Harness Bot")
    run_cmd(repo, "git", "config", "user.email", "harness@example.com")
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    run_cmd(repo, "git", "add", "seed.txt")
    run_cmd(repo, "git", "commit", "-q", "-m", "seed")
    return repo


def assert_contains(haystack: str, needle: str) -> bool:
    return needle in haystack


def scenario_orphaned_worktree(work_root: Path) -> bool:
    repo = make_repo(work_root, "orphaned-worktree")
    run_cmd(repo, "git", "branch", "repair-me")
    wt = work_root / "orphaned-worktree-wt"
    run_cmd(repo, "git", "worktree", "add", "-q", str(wt), "repair-me")
    if wt.exists():
        shutil.rmtree(wt, ignore_errors=True)
    r = subprocess.run(
        [sys.executable, str(GUIDED_SCRIPT), "--repo", str(repo)],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(SCRIPT_DIR),
    )
    out = r.stdout or ""
    return assert_contains(out, "[orphaned-worktree-metadata]") and assert_contains(out, "git worktree prune -v")


def scenario_detached_head(work_root: Path) -> bool:
    repo = make_repo(work_root, "detached-head")
    run_cmd(repo, "git", "checkout", "-q", "--detach")
    r = subprocess.run(
        [sys.executable, str(GUIDED_SCRIPT), "--repo", str(repo)],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(SCRIPT_DIR),
    )
    out = r.stdout or ""
    return assert_contains(out, "[detached-head-state]") and assert_contains(out, "git reflog --date=iso -n 20")


def scenario_zero_hash_worktree(work_root: Path) -> bool:
    repo = make_repo(work_root, "zero-hash-worktree")
    run_cmd(repo, "git", "branch", "zero-head")
    wt = work_root / "zero-hash-worktree-wt"
    run_cmd(repo, "git", "worktree", "add", "-q", str(wt), "zero-head")
    wt_meta = Path(repo / ".git" / "worktrees")
    if wt_meta.is_dir():
        for d in wt_meta.iterdir():
            if d.is_dir():
                (d / "HEAD").write_text("0000000000000000000000000000000000000000\n", encoding="utf-8")
                break
    r = subprocess.run(
        [sys.executable, str(GUIDED_SCRIPT), "--repo", str(repo)],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(SCRIPT_DIR),
    )
    out = r.stdout or ""
    return assert_contains(out, "[zero-hash-worktree-entry]")


def scenario_manual_phantom_branch_lock(work_root: Path) -> bool:
    r = subprocess.run(
        [sys.executable, str(GUIDED_SCRIPT), "--symptom", "phantom-branch-lock"],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(SCRIPT_DIR),
    )
    out = r.stdout or ""
    return assert_contains(out, "[phantom-branch-lock]") and assert_contains(out, "git worktree list --porcelain")


def run_scenario(name: str, work_root: Path) -> bool:
    if name == "orphaned-worktree":
        return scenario_orphaned_worktree(work_root)
    if name == "detached-head":
        return scenario_detached_head(work_root)
    if name == "zero-hash-worktree":
        return scenario_zero_hash_worktree(work_root)
    if name == "manual-phantom-branch-lock":
        return scenario_manual_phantom_branch_lock(work_root)
    print(f"Error: unknown scenario '{name}'", file=sys.stderr)
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description="Regression harness for Git state repair plans.")
    ap.add_argument("--scenario", metavar="NAME", help="Run single scenario")
    ap.add_argument("--list", action="store_true", help="List scenarios")
    ap.add_argument("--keep-temp", action="store_true", help="Keep temp workspace")
    args = ap.parse_args()

    if args.list:
        for s in SCENARIOS:
            print(s)
        return 0

    if not GUIDED_SCRIPT.is_file():
        print(f"Error: guided script not found: {GUIDED_SCRIPT}", file=sys.stderr)
        return 2

    scenarios = [args.scenario] if args.scenario else SCENARIOS
    if args.scenario:
        try:
            _sanitize(args.scenario)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 2
        if args.scenario not in SCENARIOS:
            print(f"Error: unknown scenario '{args.scenario}'", file=sys.stderr)
            return 2

    work_root = Path(tempfile.mkdtemp(prefix="git-state-harness-"))
    try:
        pass_count = 0
        fail_count = 0
        for scenario in scenarios:
            if run_scenario(scenario, work_root):
                print(f"PASS {scenario}")
                pass_count += 1
            else:
                print(f"FAIL {scenario}")
                fail_count += 1
        print()
        print(f"Harness result: {pass_count} passed, {fail_count} failed")
        return 0 if fail_count == 0 else 1
    finally:
        if not args.keep_temp and work_root.exists():
            shutil.rmtree(work_root, ignore_errors=True)
        elif args.keep_temp:
            print(f"Keeping harness workspace: {work_root}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())

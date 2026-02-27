#!/usr/bin/env python3
# Purpose: Arbiter Zebu CLI (push, get, status). Framework tooling for localsetup-arbiter skill.
# Created: 2026-02-20
# Last updated: 2026-02-20

"""
Arbiter CLI: create and query decision plans for async human review.
Subcommands: push, get, status. Requires arbiter-push (Arbiter Zebu) for full functionality.
"""

import argparse
import sys
from pathlib import Path

DESCRIPTION_MAX = 1024
TAG_MAX = 128
PLAN_ID_MAX = 256


def _sanitize(s: str, max_len: int, name: str) -> str:
    if not isinstance(s, str):
        raise ValueError(f"{name}: expected string, got {type(s).__name__}")
    s = " ".join(s.split())
    if len(s) > max_len:
        raise ValueError(f"{name}: length {len(s)} exceeds max {max_len}")
    if not s.strip():
        raise ValueError(f"{name}: empty after trim")
    return s.strip()


def _ensure_queue_dir() -> Path:
    base = Path.home() / ".arbiter" / "queue"
    for sub in ("pending", "completed"):
        (base / sub).mkdir(parents=True, exist_ok=True)
    return base


def cmd_push(args: argparse.Namespace) -> int:
    tag = _sanitize(args.tag, TAG_MAX, "tag")
    title = _sanitize(args.title, DESCRIPTION_MAX, "title")
    _ensure_queue_dir()
    print("[WARNING] arbiter push - Not yet implemented", file=sys.stderr)
    print("This will create decision files in ~/.arbiter/queue/pending/", file=sys.stderr)
    return 1


def cmd_get(args: argparse.Namespace) -> int:
    plan_id = _sanitize(args.plan_id, PLAN_ID_MAX, "plan_id")
    _ensure_queue_dir()
    print("[WARNING] arbiter get - Not yet implemented", file=sys.stderr)
    print("This will retrieve answers from ~/.arbiter/queue/completed/", file=sys.stderr)
    return 1


def cmd_status(args: argparse.Namespace) -> int:
    plan_id = _sanitize(args.plan_id, PLAN_ID_MAX, "plan_id")
    _ensure_queue_dir()
    print("[WARNING] arbiter status - Not yet implemented", file=sys.stderr)
    print("This will check decision file status in ~/.arbiter/queue/", file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="arbiter_cli",
        description="Arbiter Zebu CLI: push decisions, get answers, check status.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_push = sub.add_parser("push", help="Create a decision plan in the queue")
    p_push.add_argument("tag", help="Tag for filtering (e.g. project name)")
    p_push.add_argument("title", help="Plan title")
    p_push.set_defaults(func=cmd_push)

    p_get = sub.add_parser("get", help="Retrieve answers from a completed plan")
    p_get.add_argument("plan_id", help="Plan ID")
    p_get.set_defaults(func=cmd_get)

    p_status = sub.add_parser("status", help="Check status of a decision plan")
    p_status.add_argument("plan_id", help="Plan ID")
    p_status.set_defaults(func=cmd_status)

    try:
        args = parser.parse_args()
        return args.func(args)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

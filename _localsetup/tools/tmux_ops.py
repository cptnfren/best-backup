#!/usr/bin/env python3
# Purpose: Pick ops tmux session (idle = prompt regex on current line), probe sudo, send, wait; JSON out for agents.
# Created: 2026-02-25
# Last updated: 2026-02-27

"""
Tmux ops workflow tool: session pick, sudo probe, send, and adaptive wait.

Send subcommand: sends one command to the pane then sleeps a fixed pylon-guard delay (default 0.5 s)
to avoid commands racing ahead of output on high-latency links. Use --wait to additionally poll for
idle confirmation after the pylon guard.

Wait subcommand: polls pane idle state using a three-phase ladder:
  Fast   (0-2s):   poll every 0.05 s  — sub-second and quick commands
  Medium (2-15s):  poll every 0.3 s   — most real ops (git, scripts, pip install)
  Slow   (15s+):   poll every 1.0 s   — long builds, apt upgrade, dogfood runs
Idle = cursor_y changed from pre-send snapshot AND cursor line matches shell prompt regex.
On timeout: returns timed_out=true with current cursor_line so the agent can decide next action.

Output is always JSON. Hardened per INPUT_HARDENING_STANDARD: sanitized input, actionable errors
to stderr + JSON for agents.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from collections import namedtuple
from typing import Any

# Default delay after each send (seconds). Overridable via TMUX_OPS_SEND_DELAY or --delay.
DEFAULT_SEND_DELAY = 0.5
# Max command length for send (bytes, after stripping control chars). Prevents abuse and tmux issues.
MAX_CMD_LEN = 32768

# Three-phase poll ladder for cmd_wait.
FAST_POLL_INTERVAL  = 0.05   # s, fast phase (0 - FAST_PHASE_DURATION)
FAST_PHASE_DURATION = 2.0    # s
MED_POLL_INTERVAL   = 0.3    # s, medium phase (FAST_PHASE_DURATION - MED_PHASE_DURATION)
MED_PHASE_DURATION  = 15.0   # s
SLOW_POLL_INTERVAL  = 1.0    # s, slow phase (MED_PHASE_DURATION+)
DEFAULT_WAIT_TIMEOUT = 30.0  # s, default total timeout for wait / send --wait

# Default idle prompt regex string. Overridable via TMUX_OPS_IDLE_RE env var or --idle-re arg.
DEFAULT_IDLE_RE_STR = r"^.*[$#]\s*$"

TmuxResult = namedtuple("TmuxResult", ("returncode", "stdout", "stderr"))

# Session name sequence: ops, ops1, ops2, ...
OPS_BASE = "ops"
SESSION_PATTERN = re.compile(r"^ops(\d*)$")
MAX_SESSION_NUM = 20

# Idle = current line looks like a shell prompt (ends with $ or #, optional trailing space).
# Compiled from DEFAULT_IDLE_RE_STR, respecting TMUX_OPS_IDLE_RE env var at import time.
IDLE_PROMPT_RE = re.compile(
    os.environ.get("TMUX_OPS_IDLE_RE", DEFAULT_IDLE_RE_STR)
)

# Sudo probe: after sending trigger, look for these in pane
SUDO_READY_MARKER = "SUDO_READY"
PASSWORD_PROMPT_RE = re.compile(r"\[sudo\]\s*password\s+for", re.I)

# Strip only ASCII control characters that are not valid in shell command strings.
# POSIX/bash legal in command input: printable (0x20-0x7e), tab (0x09), newline (0x0a), CR (0x0d).
# We keep those; strip C0 (0x00-0x1f) except 09/0a/0d, and DEL (0x7f), to avoid injection and undefined behavior.
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _strip_control(s: str) -> str:
    """Remove control characters so input is safe for tmux and logging."""
    if not s:
        return s
    return _CONTROL_CHARS.sub("", s)


def _run_tmux(args: list[str], timeout: int = 5) -> TmuxResult:
    """Run tmux; return (returncode, stdout, stderr). On timeout/OSError return -1 and message in stderr."""
    cmd = ["tmux"] + args
    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            errors="replace",
        )
        return TmuxResult(r.returncode, r.stdout or "", r.stderr or "")
    except subprocess.TimeoutExpired as e:
        return TmuxResult(-1, "", f"tmux timeout after {e.timeout}s: {e.cmd}")
    except OSError as e:
        return TmuxResult(-1, "", f"tmux execution failed: {type(e).__name__}: {e}")


def _session_list() -> tuple[set[str] | None, str | None]:
    """Return (set of session names, None) or (None, error_detail)."""
    result = _run_tmux(["list-sessions", "-F", "#{session_name}"])
    if result.returncode != 0:
        return None, (result.stderr or f"tmux list-sessions exited {result.returncode}")
    return {s.strip() for s in result.stdout.strip().splitlines() if s.strip()}, None


def _cursor_y(target: str) -> tuple[int | None, str | None]:
    """Get cursor Y (0-based). Returns (y, None) or (None, error_detail)."""
    result = _run_tmux(["display-message", "-t", target, "-p", "-F", "#{cursor_y}"])
    if result.returncode != 0:
        return None, (result.stderr or f"tmux display-message exited {result.returncode}")
    try:
        return int(result.stdout.strip()), None
    except ValueError:
        return None, f"invalid cursor_y output: {result.stdout!r}"


def _snapshot_cursor(target: str) -> int | None:
    """Return current cursor_y or None on error. Call before send to establish baseline for cursor-delta guard."""
    cy, _ = _cursor_y(target)
    return cy


def _capture_line(target: str, line_index: int) -> tuple[str, str | None]:
    """Capture one line from target pane. Returns (line, None) or ('', error_detail)."""
    result = _run_tmux([
        "capture-pane", "-t", target, "-p", "-S", str(line_index), "-E", str(line_index),
    ])
    if result.returncode != 0:
        return "", (result.stderr or f"tmux capture-pane exited {result.returncode}")
    return result.stdout.strip(), None


def _is_pane_idle(target: str, idle_re: re.Pattern | None = None) -> bool:
    """
    Idle = the current line (where cursor is) looks like a shell prompt.
    Uses cursor_y and captures only that line; matches idle_re or IDLE_PROMPT_RE. Returns False on any error.
    """
    pattern = idle_re or IDLE_PROMPT_RE
    cy, _ = _cursor_y(target)
    if cy is None:
        return False
    line, _ = _capture_line(target, cy)
    return bool(pattern.match(line))


def _is_pane_waiting_sudo(target: str) -> bool:
    """
    Cursor is on the sudo password prompt line. Session is still usable:
    we can reuse it, probe will return password_required, user enters password.
    """
    cy, _ = _cursor_y(target)
    if cy is None:
        return False
    line, _ = _capture_line(target, cy)
    return bool(PASSWORD_PROMPT_RE.search(line))


def _ops_session_sequence() -> list[str]:
    """Yield ops, ops1, ops2, ... up to MAX_SESSION_NUM."""
    out = [OPS_BASE]
    for i in range(1, MAX_SESSION_NUM + 1):
        out.append(f"{OPS_BASE}{i}")
    return out


def _sanitize_session(name: str) -> str | None:
    """Allow only ops or opsN; strip control chars. Return name if valid, else None."""
    if not name or not isinstance(name, str):
        return None
    s = _strip_control(name.strip())
    if len(s) > 32 or SESSION_PATTERN.fullmatch(s) is None:
        return None
    return s


def _compile_idle_re(pattern_str: str | None) -> tuple[re.Pattern | None, str | None]:
    """
    Compile an idle regex string. Returns (pattern, None) or (None, error_message).
    If pattern_str is None, returns (None, None) — caller should use IDLE_PROMPT_RE default.
    """
    if pattern_str is None:
        return None, None
    try:
        return re.compile(pattern_str), None
    except re.error as e:
        return None, f"invalid regex {pattern_str!r}: {e}"


def cmd_pick() -> dict[str, Any]:
    """
    Pick first available session in ops, ops1, ops2, ...
    Available = session does not exist, or exists and (idle or waiting for sudo).
    Waiting for sudo = cursor on password prompt line; we reuse it, probe returns
    password_required, user enters password.
    """
    existing, list_err = _session_list()
    if list_err is not None:
        return {"error": "tmux list-sessions failed", "detail": list_err, "source": "pick"}
    for name in _ops_session_sequence():
        if name not in existing:
            return {"session": name, "reason": "created"}
        if _is_pane_idle(name):
            return {"session": name, "reason": "idle"}
        if _is_pane_waiting_sudo(name):
            return {"session": name, "reason": "waiting_sudo"}
    return {"session": _ops_session_sequence()[-1], "reason": "fallback"}


def cmd_probe(target: str, wait_s: float = 4.0) -> dict[str, Any]:
    """
    Send sudo trigger to target, wait, capture pane; return ready or password_required.
    Does not send any other input.
    """
    san = _sanitize_session(target)
    if san is None:
        return {"error": "invalid session name", "session": target, "source": "probe"}

    r = _run_tmux(["send-keys", "-t", san, "sudo -v && echo SUDO_READY", "Enter"])
    if r.returncode != 0:
        return {"error": "tmux send-keys failed", "detail": r.stderr, "session": san, "source": "probe"}
    time.sleep(wait_s)

    cy, cy_err = _cursor_y(san)
    if cy_err is not None:
        return {"error": "cursor position failed", "detail": cy_err, "session": san, "source": "probe"}
    current_line, cap_err = _capture_line(san, cy)
    if cap_err is not None:
        return {"error": "capture pane failed", "detail": cap_err, "session": san, "source": "probe"}

    if PASSWORD_PROMPT_RE.search(current_line):
        return {"session": san, "sudo": "password_required"}
    if SUDO_READY_MARKER in current_line or IDLE_PROMPT_RE.match(current_line):
        return {"session": san, "sudo": "ready"}
    return {"session": san, "sudo": "unknown", "hint": "check pane for prompt or error"}


def cmd_wait(
    target: str,
    timeout: float = DEFAULT_WAIT_TIMEOUT,
    idle_re: re.Pattern | None = None,
    pre_cursor_y: int | None = None,
) -> dict[str, Any]:
    """
    Poll pane idle state using a three-phase ladder until idle or timeout.

    Idle condition: cursor_y changed from pre_cursor_y (if provided) AND cursor line matches
    idle_re (or IDLE_PROMPT_RE). The cursor-delta guard prevents false positives when the cursor
    is already on a prompt line before the command begins executing.

    If pre_cursor_y is None, the cursor-delta guard is skipped (safe for standalone wait calls
    where no pre-send snapshot is available).

    Returns flat JSON. timed_out=True is an expected outcome (exit code 0), not an error.
    On timeout, cursor_line is included so the agent can inspect pane state without a second call.
    """
    san = _sanitize_session(target)
    if san is None:
        return {"error": "invalid session name", "session": target, "source": "wait"}

    pattern = idle_re or IDLE_PROMPT_RE
    start = time.monotonic()
    polls = 0

    while True:
        elapsed = time.monotonic() - start

        if elapsed >= timeout:
            cy, _ = _cursor_y(san)
            cursor_line = ""
            if cy is not None:
                cursor_line, _ = _capture_line(san, cy)
            return {
                "session": san,
                "idle": False,
                "elapsed_s": round(elapsed, 3),
                "polls": polls,
                "timed_out": True,
                "cursor_line": cursor_line,
            }

        # Determine poll interval from phase
        if elapsed < FAST_PHASE_DURATION:
            interval = FAST_POLL_INTERVAL
        elif elapsed < MED_PHASE_DURATION:
            interval = MED_POLL_INTERVAL
        else:
            interval = SLOW_POLL_INTERVAL

        time.sleep(interval)
        polls += 1

        cy, _ = _cursor_y(san)
        if cy is None:
            continue
        # Cursor-delta guard: require cursor to have moved from pre-send position
        if pre_cursor_y is not None and cy == pre_cursor_y:
            continue
        line, _ = _capture_line(san, cy)
        if pattern.match(line):
            return {
                "session": san,
                "idle": True,
                "elapsed_s": round(time.monotonic() - start, 3),
                "polls": polls,
            }


def _sanitize_command(raw: str) -> tuple[str | None, str | None]:
    """
    Sanitize command for send: strip control chars, enforce max length.
    Returns (sanitized_string, None) or (None, error_message).
    """
    if not raw or not isinstance(raw, str):
        return None, "empty or non-string command"
    s = _strip_control(raw.strip())
    if not s:
        return None, "command empty after sanitization"
    if len(s) > MAX_CMD_LEN:
        return None, f"command exceeds max length {MAX_CMD_LEN} (got {len(s)})"
    return s, None


def cmd_send(
    target: str,
    command: str,
    delay: float | None = None,
    wait: bool = False,
    wait_timeout: float = DEFAULT_WAIT_TIMEOUT,
    idle_re: re.Pattern | None = None,
) -> dict[str, Any]:
    """
    Send one command to the target pane (send-keys + Enter), then sleep `delay` seconds (pylon guard).
    If wait=True, additionally poll for idle using cmd_wait after the pylon guard.
    Snapshot cursor_y before send to enable the cursor-delta guard in cmd_wait.
    Command is sanitized (control chars stripped, max length enforced).
    """
    san = _sanitize_session(target)
    if san is None:
        return {"error": "invalid session name", "session": target, "source": "send"}
    cmd, cmd_err = _sanitize_command(command)
    if cmd_err is not None:
        return {"error": "invalid command", "detail": cmd_err, "session": san, "source": "send"}
    if delay is None:
        try:
            delay = float(os.environ.get("TMUX_OPS_SEND_DELAY", str(DEFAULT_SEND_DELAY)))
        except ValueError:
            delay = DEFAULT_SEND_DELAY
    if delay < 0:
        return {"error": "delay must be non-negative", "detail": str(delay), "session": san, "source": "send"}

    pre_cy = _snapshot_cursor(san)

    r = _run_tmux(["send-keys", "-t", san, cmd, "Enter"])
    if r.returncode != 0:
        return {"error": "tmux send-keys failed", "detail": r.stderr, "session": san, "source": "send"}
    time.sleep(delay)

    result: dict[str, Any] = {"session": san, "sent": True, "delay_s": delay}
    if wait:
        w = cmd_wait(san, wait_timeout, idle_re, pre_cursor_y=pre_cy)
        result.update({k: v for k, v in w.items() if k != "session"})
    return result


def _emit_error(out: dict[str, Any]) -> None:
    """Write actionable error to stderr for agents: error + detail + source when present."""
    err = out.get("error", "unknown error")
    detail = out.get("detail", "")
    source = out.get("source", "")
    parts = [f"tmux_ops: {err}"]
    if detail:
        parts.append(f" detail={detail}")
    if source:
        parts.append(f" source={source}")
    sys.stderr.write("".join(parts) + "\n")


def main() -> int:
    try:
        parser = argparse.ArgumentParser(description="Tmux ops: pick session, probe sudo, send, wait (hardened).")
        subparsers = parser.add_subparsers(dest="command", required=True)

        subparsers.add_parser("pick", help="Pick first available ops session (idle = prompt on current line)")

        probe_p = subparsers.add_parser("probe", help="Send sudo trigger and return ready vs password_required")
        probe_p.add_argument("-t", "--target", required=True, metavar="SESSION", help="Session name (e.g. ops)")

        send_p = subparsers.add_parser(
            "send",
            help="Send one command to pane (pylon guard only by default; use --wait for idle confirmation)",
        )
        send_p.add_argument("-t", "--target", required=True, metavar="SESSION", help="Session name (e.g. ops)")
        send_p.add_argument(
            "-d", "--delay", type=float, default=None, metavar="SECS",
            help=f"Pylon-guard sleep after send (default: {DEFAULT_SEND_DELAY}, or env TMUX_OPS_SEND_DELAY)",
        )
        send_p.add_argument(
            "--wait", action="store_true", default=False,
            help="After pylon guard, poll pane for idle (use for commands expected to finish)",
        )
        send_p.add_argument(
            "--wait-timeout", type=float, default=DEFAULT_WAIT_TIMEOUT, metavar="SECS",
            help=f"Max seconds to wait for idle when --wait is used (default: {DEFAULT_WAIT_TIMEOUT})",
        )
        send_p.add_argument(
            "--idle-re", default=None, metavar="PATTERN",
            help="Custom idle prompt regex (default: TMUX_OPS_IDLE_RE env or built-in)",
        )
        send_p.add_argument("cmd", nargs=1, metavar="CMD", help="Single command string to send (then Enter)")

        wait_p = subparsers.add_parser(
            "wait",
            help="Poll pane until idle (three-phase ladder) or timeout; returns idle/timed_out JSON",
        )
        wait_p.add_argument("-t", "--target", required=True, metavar="SESSION", help="Session name (e.g. ops)")
        wait_p.add_argument(
            "--timeout", type=float, default=DEFAULT_WAIT_TIMEOUT, metavar="SECS",
            help=f"Max seconds to poll (default: {DEFAULT_WAIT_TIMEOUT})",
        )
        wait_p.add_argument(
            "--idle-re", default=None, metavar="PATTERN",
            help="Custom idle prompt regex (default: TMUX_OPS_IDLE_RE env or built-in)",
        )
        wait_p.add_argument(
            "--pre-cursor-y", type=int, default=None, metavar="N",
            help="Cursor Y snapshot before send (enables cursor-delta guard; prevents false idle on pre-existing prompt)",
        )

        args = parser.parse_args()

        out: dict[str, Any]
        if args.command == "pick":
            out = cmd_pick()
        elif args.command == "probe":
            out = cmd_probe(args.target)
        elif args.command == "send":
            idle_re, re_err = _compile_idle_re(args.idle_re)
            if re_err is not None:
                out = {"error": "invalid --idle-re pattern", "detail": re_err, "source": "send"}
                _emit_error(out)
                print(json.dumps(out))
                return 1
            out = cmd_send(
                args.target, args.cmd[0], args.delay,
                wait=args.wait,
                wait_timeout=args.wait_timeout,
                idle_re=idle_re,
            )
        elif args.command == "wait":
            idle_re, re_err = _compile_idle_re(args.idle_re)
            if re_err is not None:
                out = {"error": "invalid --idle-re pattern", "detail": re_err, "source": "wait"}
                _emit_error(out)
                print(json.dumps(out))
                return 1
            out = cmd_wait(
                args.target,
                timeout=args.timeout,
                idle_re=idle_re,
                pre_cursor_y=args.pre_cursor_y,
            )
        else:
            out = {"error": "unknown command", "source": "main"}
            _emit_error(out)
            print(json.dumps(out))
            return 1

        if "error" in out:
            _emit_error(out)
        print(json.dumps(out))
        return 0 if "error" not in out else 1

    except Exception as e:
        err_payload = {
            "error": "unexpected exception",
            "exception_type": type(e).__name__,
            "exception_message": str(e),
            "source": "main",
        }
        _emit_error(err_payload)
        print(json.dumps(err_payload))
        if os.environ.get("LOCALSETUP_DEBUG"):
            import traceback
            sys.stderr.write(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())

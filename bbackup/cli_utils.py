"""
bbackup/cli_utils.py
Purpose: Shared CLI utilities for AI-agent-friendly JSON I/O layer.
         Provides decorators, the standard JSON envelope, exit constants,
         environment variable constants, and helper functions used by
         both bbackup/cli.py and bbman.py.
Created: 2026-02-27
Last Updated: 2026-02-27
"""

import json
import os
import sys
from typing import Any, Dict, List, Optional

import click

# ---------------------------------------------------------------------------
# Environment variable names (agents set these once; all commands inherit)
# ---------------------------------------------------------------------------

BBACKUP_OUTPUT_ENV = "BBACKUP_OUTPUT"
BBACKUP_NO_INTERACTIVE_ENV = "BBACKUP_NO_INTERACTIVE"

# ---------------------------------------------------------------------------
# Exit codes
# ---------------------------------------------------------------------------

EXIT_SUCCESS = 0       # fully successful
EXIT_USER_ERROR = 1    # bad arg, missing param, invalid --input-json
EXIT_CONFIG_ERROR = 2  # config not found or fails validation
EXIT_SYSTEM_ERROR = 3  # Docker unreachable, rsync/rclone missing, key gen failed
EXIT_PARTIAL = 4       # some items succeeded, some failed
EXIT_CANCELLED = 5     # operation cancelled by user or agent

# ---------------------------------------------------------------------------
# JSON envelope
# ---------------------------------------------------------------------------

ENVELOPE_SCHEMA_VERSION = "1"


def _build_envelope(
    command: str,
    data: Dict[str, Any],
    success: bool = True,
    errors: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return {
        "schema_version": ENVELOPE_SCHEMA_VERSION,
        "command": command,
        "success": success,
        "data": data,
        "errors": errors or [],
    }


def render_output(
    data: Dict[str, Any],
    output_fmt: str,
    command: str,
    success: bool = True,
    errors: Optional[List[str]] = None,
) -> None:
    """
    Emit the standard JSON envelope to stdout when output_fmt == 'json'.
    In text mode this is a no-op; the caller handles Rich table rendering.
    All structured JSON goes to stdout; diagnostic text goes to stderr.
    """
    if output_fmt != "json":
        return
    envelope = _build_envelope(command, data, success=success, errors=errors)
    sys.stdout.write(json.dumps(envelope, indent=2, default=str) + "\n")
    sys.stdout.flush()


def json_error(
    command: str,
    message: str,
    exit_code: int = EXIT_USER_ERROR,
    output_fmt: str = "json",
) -> None:
    """
    Emit an error envelope to stdout (JSON mode) or a plain message to stderr
    (text mode), then exit with exit_code.

    Call this for fatal errors that occur before a command can produce output
    (e.g., unknown backup set, missing required path, invalid --input-json).
    This replaces bare sys.exit(1) + console.print() pairs throughout cli.py
    and bbman.py, routing errors correctly for both human and agent consumers.
    """
    if output_fmt == "json":
        envelope = _build_envelope(command, {}, success=False, errors=[message])
        sys.stdout.write(json.dumps(envelope, indent=2, default=str) + "\n")
        sys.stdout.flush()
    else:
        sys.stderr.write(f"Error: {message}\n")
        sys.stderr.flush()
    sys.exit(exit_code)

# ---------------------------------------------------------------------------
# Reusable decorators
# ---------------------------------------------------------------------------


def output_option(f):
    """
    Adds --output / -o [text|json] to a Click command.
    Defaults to the BBACKUP_OUTPUT env var, then 'text'.
    The default is evaluated lazily at invocation time so env var changes
    (e.g. in tests) are always picked up.
    """
    def _default():
        return os.environ.get(BBACKUP_OUTPUT_ENV, "text")

    return click.option(
        "--output",
        "-o",
        type=click.Choice(["text", "json"]),
        default=_default,
        show_default=True,
        help=(
            "Output format. 'json' emits a machine-readable envelope to stdout. "
            "Set BBACKUP_OUTPUT=json to default all commands to JSON."
        ),
    )(f)


def input_json_option(f):
    """
    Adds --input-json to a Click command.
    Accepts a flat JSON object whose keys map to option names
    (hyphens converted to underscores). Merges over any CLI flags.
    """
    return click.option(
        "--input-json",
        default=None,
        metavar="JSON",
        help=(
            "Supply all parameters as a flat JSON object. Keys match option "
            "names (hyphens -> underscores). Merges over CLI flags provided. "
            "Unknown keys are ignored. Example: "
            '--input-json \'{"containers": ["myapp"], "incremental": true}\''
        ),
    )(f)


def dry_run_option(f):
    """
    Adds --dry-run to a Click command (backup and restore only).
    In dry-run mode the command resolves its target list and returns a JSON
    plan without executing any backup or restore operations.
    """
    return click.option(
        "--dry-run",
        is_flag=True,
        default=False,
        help=(
            "Resolve and display what would be backed up / restored without "
            "executing. Always returns JSON. Exits 0 on a valid plan."
        ),
    )(f)

# ---------------------------------------------------------------------------
# merge_json_input
# ---------------------------------------------------------------------------


def merge_json_input(ctx: click.Context, input_json: Optional[str]) -> None:
    """
    Parse --input-json and overwrite matching keys in ctx.params in-place.
    Must be called at the top of every command body before any other logic.

    - Invalid JSON exits with EXIT_USER_ERROR.
    - Non-object JSON (list, scalar) exits with EXIT_USER_ERROR.
    - Unknown keys are silently ignored (forward-compatible).
    - Matched keys overwrite any value set by CLI flags.
    """
    if not input_json:
        return
    try:
        data = json.loads(input_json)
    except json.JSONDecodeError as exc:
        output_fmt = ctx.params.get("output", os.environ.get(BBACKUP_OUTPUT_ENV, "text"))
        json_error(
            ctx.info_name or "unknown",
            f"--input-json is not valid JSON: {exc}",
            EXIT_USER_ERROR,
            output_fmt,
        )
        return  # unreachable; json_error exits
    if not isinstance(data, dict):
        output_fmt = ctx.params.get("output", os.environ.get(BBACKUP_OUTPUT_ENV, "text"))
        json_error(
            ctx.info_name or "unknown",
            "--input-json must be a JSON object {}, not a list or scalar",
            EXIT_USER_ERROR,
            output_fmt,
        )
        return
    for key, value in data.items():
        if key in ctx.params:
            ctx.params[key] = value

# ---------------------------------------------------------------------------
# flatten_health_tuples
# ---------------------------------------------------------------------------


def flatten_health_tuples(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert positional tuple values in health/deps result dicts to named
    sub-dicts so agents can address fields by name rather than by index.

    Handles three shapes:
      Tuple[bool, str]              -> {"ok": bool, "message": str}
      Tuple[bool, List, List]       -> {"ok": bool, "installed": [...], "missing": [...]}
      Any other value               -> passed through unchanged

    Example input  (from health.run_health_check()):
      {"docker": (True, "Docker 24.0.5 accessible"),
       "python_packages": (True, ["rich", "click"], [])}

    Example output:
      {"docker": {"ok": True, "message": "Docker 24.0.5 accessible"},
       "python_packages": {"ok": True, "installed": ["rich", "click"], "missing": []}}
    """
    out: Dict[str, Any] = {}
    for key, value in raw.items():
        if isinstance(value, tuple):
            if len(value) == 2 and isinstance(value[0], bool):
                out[key] = {"ok": value[0], "message": value[1]}
            elif len(value) == 3 and isinstance(value[0], bool):
                out[key] = {
                    "ok": value[0],
                    "installed": value[1],
                    "missing": value[2],
                }
            else:
                out[key] = list(value)
        else:
            out[key] = value
    return out

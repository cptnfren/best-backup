"""
bbackup/cli_metadata.py
Purpose: Structured metadata for all bbackup and bbman CLI commands, parameters,
         JSON fields, and examples. This is the single source of truth for the
         skills ecosystem, the generated Markdown catalog, and future tooling.
Created: 2026-03-04
Last Updated: 2026-03-04
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


CliName = Literal["bbackup", "bbman"]
ParamKind = Literal["flag", "positional", "json_field", "env_var"]
ShapeKind = Literal["scalar", "enum", "list", "map", "object"]


@dataclass
class Parameter:
    """
    Canonical description of a single parameter exposed by a CLI command.

    This covers both CLI flags/positionals and JSON / env inputs so that a
    single registry can drive skills JSON, Markdown docs, and future tooling.
    """

    name: str
    kind: ParamKind
    type: str = "string"
    description: str = ""
    required: bool = False
    default: Optional[Any] = None
    allowed_values: Optional[List[Any]] = None
    shape: ShapeKind = "scalar"
    cli_flag: Optional[str] = None
    json_key: Optional[str] = None
    env_var: Optional[str] = None
    aliases: List[str] = field(default_factory=list)


@dataclass
class Example:
    """
    Example usage for a command in both CLI and JSON forms.
    """

    description: str
    cli: Optional[str] = None
    input_json: Optional[Dict[str, Any]] = None


@dataclass
class CliCommand:
    """
    Structured description of a single CLI command.
    """

    cli: CliName
    name: str
    summary: str
    description: str
    category: str
    parameters: List[Parameter] = field(default_factory=list)
    examples: List[Example] = field(default_factory=list)

    @property
    def id(self) -> str:
        return f"{self.cli}:{self.name}"


# ---------------------------------------------------------------------------
# bbackup command registry (normalized surface)
# ---------------------------------------------------------------------------


BBACKUP_COMMANDS: Dict[str, CliCommand] = {}


def _register_bbackup(cmd: CliCommand) -> None:
    BBACKUP_COMMANDS[cmd.id] = cmd


_register_bbackup(
    CliCommand(
        cli="bbackup",
        name="backup",
        summary="Create Docker and/or filesystem backup.",
        description=(
            "Back up one or more Docker containers and optional filesystem paths. "
            "Supports incremental rsync (--link-dest), multiple remotes, and "
            "non-interactive JSON-driven operation."
        ),
        category="backup",
        parameters=[
            Parameter(
                name="containers",
                kind="flag",
                type="string[]",
                description="Container names to back up (repeatable).",
                cli_flag="--containers",
                json_key="containers",
                shape="list",
            ),
            Parameter(
                name="backup_set",
                kind="flag",
                type="string",
                description="Named backup set from config.yaml.",
                cli_flag="--backup-set",
                json_key="backup_set",
            ),
            Parameter(
                name="config_only",
                kind="flag",
                type="bool",
                description="Back up only container configs (no volumes).",
                cli_flag="--config-only",
                json_key="config_only",
                default=False,
            ),
            Parameter(
                name="volumes_only",
                kind="flag",
                type="bool",
                description="Back up only volumes (no configs).",
                cli_flag="--volumes-only",
                json_key="volumes_only",
                default=False,
            ),
            Parameter(
                name="no_networks",
                kind="flag",
                type="bool",
                description="Skip network backups.",
                cli_flag="--no-networks",
                json_key="no_networks",
                default=False,
            ),
            Parameter(
                name="incremental",
                kind="flag",
                type="bool",
                description="Enable incremental backup via rsync --link-dest.",
                cli_flag="--incremental",
                json_key="incremental",
                default=False,
            ),
            Parameter(
                name="no_interactive",
                kind="flag",
                type="bool",
                description="Disable TUI and prompts; required for agent use.",
                cli_flag="--no-interactive",
                json_key="no_interactive",
                env_var="BBACKUP_NO_INTERACTIVE",
                default=False,
            ),
            Parameter(
                name="remote",
                kind="flag",
                type="string[]",
                description="Remote storage destinations (repeatable).",
                cli_flag="--remote",
                json_key="remote",
                shape="list",
            ),
            Parameter(
                name="paths",
                kind="flag",
                type="string[]",
                description="Filesystem paths to back up (repeatable).",
                cli_flag="--paths",
                json_key="paths",
                shape="list",
            ),
            Parameter(
                name="exclude",
                kind="flag",
                type="string[]",
                description="Exclude patterns for filesystem backup (repeatable).",
                cli_flag="--exclude",
                json_key="exclude",
                shape="list",
            ),
            Parameter(
                name="filesystem_set",
                kind="flag",
                type="string",
                description="Named filesystem backup set from config.yaml.",
                cli_flag="--filesystem-set",
                json_key="filesystem_set",
            ),
            Parameter(
                name="dry_run",
                kind="flag",
                type="bool",
                description="Resolve targets and return a plan without executing.",
                cli_flag="--dry-run",
                json_key="dry_run",
                default=False,
            ),
            Parameter(
                name="output",
                kind="flag",
                type="string",
                description="Output format: text or json.",
                cli_flag="--output",
                json_key="output",
                allowed_values=["text", "json"],
                shape="enum",
            ),
            Parameter(
                name="input_json",
                kind="json_field",
                type="object",
                description="Flat JSON object providing all parameters.",
                json_key=None,
                shape="object",
            ),
        ],
        examples=[
            Example(
                description="Backup specific containers non-interactively with JSON output.",
                cli="bbackup backup --containers myapp --no-interactive --output json",
            ),
            Example(
                description="Incremental backup of a named backup set to a remote.",
                cli="bbackup backup --backup-set production --incremental --remote gdrive --no-interactive --output json",
            ),
            Example(
                description="JSON-driven backup of two containers.",
                cli='bbackup backup --input-json \'{\"containers\":[\"myapp\",\"mydb\"],\"incremental\":true,\"no_interactive\":true}\' --output json',
                input_json={
                    "containers": ["myapp", "mydb"],
                    "incremental": True,
                    "no_interactive": True,
                    "output": "json",
                },
            ),
            Example(
                description="Dry-run to see what would be backed up.",
                cli="bbackup backup --backup-set production --dry-run --no-interactive --output json",
                input_json={"backup_set": "production", "dry_run": True, "no_interactive": True, "output": "json"},
            ),
        ],
    )
)


_register_bbackup(
    CliCommand(
        cli="bbackup",
        name="restore",
        summary="Restore containers, volumes, networks, or filesystem paths from a backup.",
        description=(
            "Restore Docker resources and filesystem targets from a backup directory. "
            "Supports full restores, targeted restores, rename mappings, and dry-run mode."
        ),
        category="restore",
        parameters=[
            Parameter(
                name="backup_path",
                kind="flag",
                type="path",
                description="Path to the backup directory.",
                cli_flag="--backup-path",
                json_key="backup_path",
                required=True,
            ),
            Parameter(
                name="all",
                kind="flag",
                type="bool",
                description="Restore all items from the backup.",
                cli_flag="--all",
                json_key="all",
                default=False,
            ),
            Parameter(
                name="containers",
                kind="flag",
                type="string[]",
                description="Specific container names to restore (repeatable).",
                cli_flag="--containers",
                json_key="containers",
                shape="list",
            ),
            Parameter(
                name="volumes",
                kind="flag",
                type="string[]",
                description="Specific volume names to restore (repeatable).",
                cli_flag="--volumes",
                json_key="volumes",
                shape="list",
            ),
            Parameter(
                name="networks",
                kind="flag",
                type="string[]",
                description="Specific network names to restore (repeatable).",
                cli_flag="--networks",
                json_key="networks",
                shape="list",
            ),
            Parameter(
                name="filesystem",
                kind="flag",
                type="string[]",
                description="Filesystem target names to restore (repeatable).",
                cli_flag="--filesystem",
                json_key="filesystem",
                shape="list",
            ),
            Parameter(
                name="filesystem_destination",
                kind="flag",
                type="path",
                description="Destination path for filesystem restore.",
                cli_flag="--filesystem-destination",
                json_key="filesystem_destination",
            ),
            Parameter(
                name="rename",
                kind="flag",
                type="string[]",
                description="Rename mappings in old:new format (repeatable).",
                cli_flag="--rename",
                json_key="rename",
                shape="list",
            ),
            Parameter(
                name="dry_run",
                kind="flag",
                type="bool",
                description="Return a restore plan without executing.",
                cli_flag="--dry-run",
                json_key="dry_run",
                default=False,
            ),
            Parameter(
                name="output",
                kind="flag",
                type="string",
                description="Output format: text or json.",
                cli_flag="--output",
                json_key="output",
                allowed_values=["text", "json"],
                shape="enum",
            ),
            Parameter(
                name="input_json",
                kind="json_field",
                type="object",
                description="Flat JSON object providing all parameters.",
                shape="object",
            ),
        ],
        examples=[
            Example(
                description="Restore everything from a backup directory.",
                cli="bbackup restore --backup-path /tmp/bbackup/backup_20260227_120000 --all --output json",
            ),
            Example(
                description="Restore a single container from a backup using JSON input.",
                cli='bbackup restore --input-json \'{"backup_path":"/tmp/bbackup/backup_20260227_120000","containers":["myapp"]}\' --output json',
                input_json={
                    "backup_path": "/tmp/bbackup/backup_20260227_120000",
                    "containers": ["myapp"],
                    "output": "json",
                },
            ),
            Example(
                description="Dry-run restore to inspect what would be restored.",
                cli="bbackup restore --backup-path /tmp/bbackup/backup_20260227_120000 --all --dry-run --output json",
                input_json={
                    "backup_path": "/tmp/bbackup/backup_20260227_120000",
                    "all": True,
                    "dry_run": True,
                    "output": "json",
                },
            ),
        ],
    )
)


# NOTE: For brevity, other bbackup commands (list-containers, list-backup-sets,
# list-filesystem-sets, list-backups, list-remote-backups, init-config,
# init-encryption, skills) will be added to BBACKUP_COMMANDS following the same
# pattern during implementation. The generator and CLI wiring will treat this
# registry as the single source of truth.


# ---------------------------------------------------------------------------
# bbman command registry (normalized surface)
# ---------------------------------------------------------------------------


BBMAN_COMMANDS: Dict[str, CliCommand] = {}


def _register_bbman(cmd: CliCommand) -> None:
    BBMAN_COMMANDS[cmd.id] = cmd


_register_bbman(
    CliCommand(
        cli="bbman",
        name="setup",
        summary="Run interactive setup wizard for first-time configuration.",
        description=(
            "Run the interactive setup wizard to create an initial config.yaml. "
            "In agent mode, use --no-interactive with BBACKUP_NO_INTERACTIVE=1 "
            "to query current state instead of running the wizard."
        ),
        category="lifecycle",
        parameters=[
            Parameter(
                name="no_interactive",
                kind="flag",
                type="bool",
                description="Skip wizard; return current config state (agent mode).",
                cli_flag="--no-interactive",
                json_key="no_interactive",
                env_var="BBACKUP_NO_INTERACTIVE",
                default=False,
            ),
            Parameter(
                name="output",
                kind="flag",
                type="string",
                description="Output format: text or json.",
                cli_flag="--output",
                json_key="output",
                allowed_values=["text", "json"],
                shape="enum",
            ),
            Parameter(
                name="input_json",
                kind="json_field",
                type="object",
                description="Flat JSON object providing all parameters.",
                shape="object",
            ),
        ],
        examples=[
            Example(
                description="Run setup in non-interactive mode for an agent.",
                cli="bbman setup --no-interactive --output json",
                input_json={"no_interactive": True, "output": "json"},
            ),
        ],
    )
)


_register_bbman(
    CliCommand(
        cli="bbman",
        name="health",
        summary="Run comprehensive health check (Docker, rsync, rclone, Python packages).",
        description=(
            "Check Docker connectivity, system tools, Python dependencies, and "
            "configuration health. Designed for both human and agent consumption."
        ),
        category="lifecycle",
        parameters=[
            Parameter(
                name="output",
                kind="flag",
                type="string",
                description="Output format: text or json.",
                cli_flag="--output",
                json_key="output",
                allowed_values=["text", "json"],
                shape="enum",
            ),
            Parameter(
                name="input_json",
                kind="json_field",
                type="object",
                description="Flat JSON object providing all parameters.",
                shape="object",
            ),
        ],
        examples=[
            Example(
                description="Run health check with JSON result.",
                cli="bbman health --output json",
                input_json={"output": "json"},
            ),
        ],
    )
)


# NOTE: As with BBACKUP_COMMANDS, additional bbman commands (check-deps,
# validate-config, status, cleanup, diagnostics, check-updates, update,
# repo-url, run, skills) will be incrementally added to BBMAN_COMMANDS with
# the same structure during implementation.


def get_command_registry(cli: CliName) -> Dict[str, CliCommand]:
    """Return the command registry for the requested CLI."""
    return BBACKUP_COMMANDS if cli == "bbackup" else BBMAN_COMMANDS


def get_command(cli: CliName, name: str) -> Optional[CliCommand]:
    """Lookup a command by cli + name. Returns None if unknown."""
    registry = get_command_registry(cli)
    return registry.get(f"{cli}:{name}")


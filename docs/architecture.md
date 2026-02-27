# Architecture

> Design decisions, module breakdown, and configuration internals for contributors and advanced users.

---

## Technology stack

| Component | Library / tool | Version |
|---|---|---|
| Language | Python | 3.10+ |
| CLI framework | Click | 8.1.7+ |
| Terminal UI | Rich | 13.7.0+ |
| Docker integration | docker-py SDK | 7.0.0+ |
| Config format | PyYAML | 6.0.1+ |
| SFTP | paramiko | 3.4.0+ |
| Encryption | cryptography | 41.0.0+ |
| HTTP (key fetching) | requests | 2.31.0+ |
| Volume backup | rsync | system |
| Cloud storage | rclone | optional |

---

## Backup strategy

The tool uses two separate mechanisms depending on what it is backing up.

**Volumes** go through rsync running inside a temporary Alpine container that mounts the target volume. This handles large datasets well and supports incremental mode via `--link-dest`, where unchanged files become hardlinks to the previous backup instead of copies.

**Metadata** (container configs, network configs, logs) goes through `tar` with configurable compression. These are small and benefit more from good compression than from rsync's delta algorithm.

The two strategies produce separate artifacts that are bundled into a timestamped backup directory before encryption and remote upload.

---

## Module responsibilities

### `bbackup/cli.py`

Click entry point for the `bbackup` command. Handles argument parsing and delegates to the appropriate class. Commands: `backup`, `restore`, `list-containers`, `list-backup-sets`, `list-backups`, `list-remote-backups`, `list-filesystem-sets`, `init-config`, `init-encryption`, `skills`.

Every command accepts `--output [text|json]`, `--input-json JSON`, and `backup`/`restore` also accept `--dry-run`. In JSON mode the command emits the standard envelope to stdout; all diagnostic text goes to stderr. The `BBACKUP_OUTPUT` and `BBACKUP_NO_INTERACTIVE` env vars apply globally.

### `bbackup/cli_utils.py`

Shared foundation for the AI-agent-friendly JSON I/O layer. Contains:

- `output_option`, `input_json_option`, `dry_run_option` -- Click decorators applied to every command.
- `merge_json_input(ctx, json_str)` -- parses `--input-json` and overwrites matching `ctx.params` keys.
- `render_output(data, fmt, command, ...)` -- writes the standard JSON envelope to stdout when `fmt == "json"`.
- `json_error(command, message, exit_code, fmt)` -- emits an error envelope (JSON mode) or stderr line (text mode) then exits.
- `flatten_health_tuples(raw)` -- converts `Tuple[bool, str]` / `Tuple[bool, List, List]` values to named dicts for JSON consumers.
- Exit constants: `EXIT_SUCCESS=0`, `EXIT_USER_ERROR=1`, `EXIT_CONFIG_ERROR=2`, `EXIT_SYSTEM_ERROR=3`, `EXIT_PARTIAL=4`, `EXIT_CANCELLED=5`.
- Env var names: `BBACKUP_OUTPUT_ENV`, `BBACKUP_NO_INTERACTIVE_ENV`.

### `bbackup/skills.py`

Static skill descriptors for AI agent capability discovery. Contains `BBACKUP_SKILLS` and `BBMAN_SKILLS` dicts keyed by skill id, and `get_skill(cli, skill_id)` accessor.

Each skill entry includes: `id`, `summary`, `workflow` (ordered command list), `steps` (each with `command`, `description`, `optional_flags`, `valid_values`, `input_json_schema`), `examples`, `output_format`, `exit_codes`.

`get_skill(cli, None)` returns a level-0 overview with `agent_hint` and a compact skills list (80-90% token savings vs loading full `--help` trees). `get_skill(cli, skill_id)` returns the full step-by-step descriptor.

### JSON envelope contract

All commands emit exactly one JSON object to **stdout** in JSON mode:

```json
{
  "schema_version": "1",
  "command": "backup",
  "success": true,
  "data": { "...command-specific fields..." },
  "errors": []
}
```

`schema_version` bumps only on breaking field removals or renames; additive fields are always backward-compatible. All diagnostic and progress text is routed to **stderr** so stdout can be parsed unambiguously.

### `bbackup/config.py`

Loads and validates the YAML config file. Discovers config location using the priority chain below. Contains all dataclasses: `BackupScope`, `BackupSet`, `RemoteStorage`, `RetentionPolicy`, `IncrementalSettings`, `EncryptionSettings`, `Config`. CLI overrides are merged on top of file defaults.

### `bbackup/docker_backup.py`

Talks to the Docker API. Starts temporary Alpine containers, mounts target volumes, and runs rsync or tar inside them. Also inspects container and network configs. All Docker API errors are caught and reported via `BackupStatus`.

### `bbackup/backup_runner.py`

Orchestrates the full backup workflow:

```
init → select items → prepare staging dir
  → backup configs → backup volumes → backup networks
  → backup filesystem paths (if filesystem_targets provided)
  → [archive metadata - TODO: create_metadata_archive() exists but not yet wired in]
  → encrypt (if enabled)
  → upload to remotes
  → rotate old backups
  → report
```

Reads and writes `BackupStatus` throughout so the TUI stays current.

### `bbackup/filesystem_backup.py`

Backs up arbitrary host filesystem paths and directory trees using rsync directly (no Docker). Key behaviors:

- Source path is rsynced to `backup_dir/filesystems/<target_name>/`
- Exclude patterns are written to a temp file and passed via `--exclude-from`; the temp file is always deleted in a `finally` block regardless of success or failure
- Incremental mode uses `--link-dest` pointing at the most recent previous `backup_YYYYMMDD_HHMMSS` sibling directory that contains the same target name. The current run directory is always excluded from the scan so a backup never links to itself
- Progress output is streamed line-by-line to the caller's callback for live TUI updates

### `bbackup/restore.py`

Reads a backup directory and restores containers, volumes, networks, and filesystem paths. Supports renaming on restore (`--rename old:new`). Handles decryption before restore when the backup is encrypted.

### `bbackup/tui.py`

Two main classes:

- `BackupStatus`: thread-safe state object (lock-protected). Tracks current action, per-item status, errors, pause/cancel flags, transfer metrics.
- `BackupTUI`: the live dashboard. Renders a BTOP-style layout at 4 fps using Rich's `Live`. Handles keyboard input (Q, P, S, H). Also provides interactive selection dialogs for containers, backup sets, and scope options.

### `bbackup/remote.py`

Abstracts three upload targets behind a common interface: local filesystem (shutil), rclone (subprocess), and SFTP (paramiko). Each remote is tried independently so one failure does not abort others. Upload progress feeds into `BackupStatus`.

### `bbackup/rotation.py`

Applies daily/weekly/monthly retention. Calculates which backups to keep and removes the rest, oldest-first. Also checks storage quota thresholds and triggers cleanup when the limit is approached.

### `bbackup/encryption.py`

Two encryption modes:

- **Symmetric**: AES-256-GCM with a per-file random IV. One key encrypts and decrypts.
- **Asymmetric**: RSA-OAEP wrapping an AES session key. The public key encrypts, the private key decrypts.

Public keys can be referenced by path, URL, or GitHub shortcut (`github:USER/gist:ID`). Fetched keys are cached at `~/.cache/bbackup/keys/` with mode 600.

### `bbackup/logging.py`

`get_logger(name)` returns a properly named logger for any module. `setup_logging(config)` configures a `RotatingFileHandler` at `~/.local/share/bbackup/bbackup.log` on startup.

### `bbackup/management/`

11-module subpackage powering the `bbman` command. Each module handles one lifecycle concern:

| Module | Responsibility |
|---|---|
| `first_run.py` | Detect first run, locate config path |
| `setup_wizard.py` | Interactive first-time setup |
| `health.py` | Docker, system tool, config health checks |
| `diagnostics.py` | Generate diagnostic report |
| `dependencies.py` | Check and install missing packages |
| `updater.py` | Self-update from remote repo |
| `version.py` | Version detection, Git-compatible checksums |
| `repo.py` | Manage update source URL |
| `config.py` | Management-layer config (separate from backup config) |
| `status.py` | Backup history and totals |
| `cleanup.py` | Staging dir and log cleanup |
| `utils.py` | Shared utilities |

---

## Configuration system

### Discovery order

1. `~/.config/bbackup/config.yaml`
2. `~/.bbackup/config.yaml`
3. `/etc/bbackup/config.yaml`
4. `./config.yaml`

### Override chain

Config file provides defaults. CLI arguments override them at runtime. Interactive selection (when `--interactive` is active, which is the default) allows further runtime changes before the backup starts.

### Configuration sections

| Section | Purpose |
|---|---|
| `backup` | Staging dir, backup sets, default scope |
| `remotes` | Remote storage destinations |
| `retention` | Daily/weekly/monthly counts, quota |
| `incremental` | Enable rsync `--link-dest` mode |
| `logging` | Log path, level, rotation |
| `encryption` | Method, key paths, algorithm |
| `docker` | Socket path, timeout |

---

## BackupStatus data flow

`BackupStatus` is the shared state object between the backup worker thread and the TUI render thread. The worker calls `status.update()`, `status.add_error()`, and updates per-item dicts. The TUI reads these on every render cycle (4 fps). A `threading.Lock` protects all writes.

---

## Known gaps

- `create_metadata_archive()` exists in `docker_backup.py` but is not yet called from `backup_runner.py`. The method produces a compressed tar of config and network metadata. Wiring it in requires adding a call after all item backups complete and before `encrypt_backup_directory()`.
- S and H keyboard shortcuts print to console rather than opening a modal overlay. Modal implementation is planned.

---

## Repository structure

```
best-backup/
├── bbackup/                # Main package
│   ├── cli.py
│   ├── config.py
│   ├── docker_backup.py
│   ├── filesystem_backup.py
│   ├── backup_runner.py
│   ├── restore.py
│   ├── tui.py
│   ├── remote.py
│   ├── rotation.py
│   ├── encryption.py
│   ├── logging.py
│   ├── bbman_entry.py
│   └── management/         # bbman subpackage
├── docs/                   # Reference documentation
│   ├── architecture.md     # This file
│   ├── management.md       # bbman reference
│   ├── encryption.md       # Encryption guide
│   └── dev/               # Internal dev notes and test logs
├── scripts/                # Test and utility scripts
├── bbackup.py              # bbackup entry point
├── bbman.py                # bbman entry point
├── config.yaml.example
├── requirements.txt
└── setup.py
```

---

Back to [README.md](../README.md).

<!-- project-footer:start -->

<br><br>

<p align="center">
Slavic Kozyuk<br>
&copy; 2026 <a href="https://www.cruxexperts.com/">Crux Experts LLC</a> &mdash; <a href="https://github.com/cptnfren/best-backup/blob/main/LICENSE">MIT License</a>
</p>

<!-- project-footer:end -->

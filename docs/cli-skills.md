# CLI skills catalog

> Generated from the bbackup/bbman CLI metadata. Version: 1.4.0. This catalog is authoritative for this version.

## bbackup

### bbackup backup

**Summary**: Create Docker and/or filesystem backup.

Back up one or more Docker containers and optional filesystem paths. Supports incremental rsync (--link-dest), multiple remotes, and non-interactive JSON-driven operation.

#### CLI parameters

| Name | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `--containers` | `string[]` | no | `` | Container names to back up (repeatable). |
| `--backup-set` | `string` | no | `` | Named backup set from config.yaml. |
| `--config-only` | `bool` | no | `False` | Back up only container configs (no volumes). |
| `--volumes-only` | `bool` | no | `False` | Back up only volumes (no configs). |
| `--no-networks` | `bool` | no | `False` | Skip network backups. |
| `--incremental` | `bool` | no | `False` | Enable incremental backup via rsync --link-dest. |
| `--no-interactive` | `bool` | no | `False` | Disable TUI and prompts; required for agent use. |
| `--remote` | `string[]` | no | `` | Remote storage destinations (repeatable). |
| `--paths` | `string[]` | no | `` | Filesystem paths to back up (repeatable). |
| `--exclude` | `string[]` | no | `` | Exclude patterns for filesystem backup (repeatable). |
| `--filesystem-set` | `string` | no | `` | Named filesystem backup set from config.yaml. |
| `--dry-run` | `bool` | no | `False` | Resolve targets and return a plan without executing. |
| `--output` | `string` | no | `` | Output format: text or json. |

#### JSON / environment parameters

| Name | Kind | Type | Required | Default | Description |
|---|---|---|:---:|---|---|
| `input_json` | json | `object` | no | `` | Flat JSON object providing all parameters. |

#### Examples

- Backup specific containers non-interactively with JSON output.

  ```bash
  bbackup backup --containers myapp --no-interactive --output json
  ```

- Incremental backup of a named backup set to a remote.

  ```bash
  bbackup backup --backup-set production --incremental --remote gdrive --no-interactive --output json
  ```

- JSON-driven backup of two containers.

  ```bash
  bbackup backup --input-json '{"containers":["myapp","mydb"],"incremental":true,"no_interactive":true}' --output json
  ```

  ```bash
  bbackup backup --input-json '{"containers":["myapp","mydb"],"incremental":true,"no_interactive":true,"output":"json"}' --output json
  ```

- Dry-run to see what would be backed up.

  ```bash
  bbackup backup --backup-set production --dry-run --no-interactive --output json
  ```

  ```bash
  bbackup backup --input-json '{"backup_set":"production","dry_run":true,"no_interactive":true,"output":"json"}' --output json
  ```

### bbackup restore

**Summary**: Restore containers, volumes, networks, or filesystem paths from a backup.

Restore Docker resources and filesystem targets from a backup directory. Supports full restores, targeted restores, rename mappings, and dry-run mode.

#### CLI parameters

| Name | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `--backup-path` | `path` | yes | `` | Path to the backup directory. |
| `--all` | `bool` | no | `False` | Restore all items from the backup. |
| `--containers` | `string[]` | no | `` | Specific container names to restore (repeatable). |
| `--volumes` | `string[]` | no | `` | Specific volume names to restore (repeatable). |
| `--networks` | `string[]` | no | `` | Specific network names to restore (repeatable). |
| `--filesystem` | `string[]` | no | `` | Filesystem target names to restore (repeatable). |
| `--filesystem-destination` | `path` | no | `` | Destination path for filesystem restore. |
| `--rename` | `string[]` | no | `` | Rename mappings in old:new format (repeatable). |
| `--dry-run` | `bool` | no | `False` | Return a restore plan without executing. |
| `--output` | `string` | no | `` | Output format: text or json. |

#### JSON / environment parameters

| Name | Kind | Type | Required | Default | Description |
|---|---|---|:---:|---|---|
| `input_json` | json | `object` | no | `` | Flat JSON object providing all parameters. |

#### Examples

- Restore everything from a backup directory.

  ```bash
  bbackup restore --backup-path /tmp/bbackup/backup_20260227_120000 --all --output json
  ```

- Restore a single container from a backup using JSON input.

  ```bash
  bbackup restore --input-json '{"backup_path":"/tmp/bbackup/backup_20260227_120000","containers":["myapp"]}' --output json
  ```

  ```bash
  bbackup restore --input-json '{"backup_path":"/tmp/bbackup/backup_20260227_120000","containers":["myapp"],"output":"json"}' --output json
  ```

- Dry-run restore to inspect what would be restored.

  ```bash
  bbackup restore --backup-path /tmp/bbackup/backup_20260227_120000 --all --dry-run --output json
  ```

  ```bash
  bbackup restore --input-json '{"backup_path":"/tmp/bbackup/backup_20260227_120000","all":true,"dry_run":true,"output":"json"}' --output json
  ```

## bbman

### bbman health

**Summary**: Run comprehensive health check (Docker, rsync, rclone, Python packages).

Check Docker connectivity, system tools, Python dependencies, and configuration health. Designed for both human and agent consumption.

#### CLI parameters

| Name | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `--output` | `string` | no | `` | Output format: text or json. |

#### JSON / environment parameters

| Name | Kind | Type | Required | Default | Description |
|---|---|---|:---:|---|---|
| `input_json` | json | `object` | no | `` | Flat JSON object providing all parameters. |

#### Examples

- Run health check with JSON result.

  ```bash
  bbman health --output json
  ```

  ```bash
  bbman health --input-json '{"output":"json"}' --output json
  ```

### bbman setup

**Summary**: Run interactive setup wizard for first-time configuration.

Run the interactive setup wizard to create an initial config.yaml. In agent mode, use --no-interactive with BBACKUP_NO_INTERACTIVE=1 to query current state instead of running the wizard.

#### CLI parameters

| Name | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `--no-interactive` | `bool` | no | `False` | Skip wizard; return current config state (agent mode). |
| `--output` | `string` | no | `` | Output format: text or json. |

#### JSON / environment parameters

| Name | Kind | Type | Required | Default | Description |
|---|---|---|:---:|---|---|
| `input_json` | json | `object` | no | `` | Flat JSON object providing all parameters. |

#### Examples

- Run setup in non-interactive mode for an agent.

  ```bash
  bbman setup --no-interactive --output json
  ```

  ```bash
  bbman setup --input-json '{"no_interactive":true,"output":"json"}' --output json
  ```


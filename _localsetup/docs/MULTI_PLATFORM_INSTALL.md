---
status: ACTIVE
version: 2.8
---

# Multi-platform install (Localsetup v2)

**Purpose:** How to install Localsetup v2 for each supported AI agent platform. Supported platforms (canonical list): [PLATFORM_REGISTRY.md](PLATFORM_REGISTRY.md). Same framework; platform-specific context loaders and skill paths. **Cross-platform:** Bash on Linux/macOS; PowerShell on Windows. The framework detects the host and uses the appropriate scripts.

## Platform detection and script selection

- **Linux / macOS:** Use the Bash scripts (`install`, `_localsetup/tools/deploy`, `verify_context`, `verify_rules`, `tests/automated_test.sh`). Same options and behavior.
- **Windows:** Use the PowerShell scripts (`install.ps1`, `_localsetup/tools/deploy.ps1`, `verify_context.ps1`, `verify_rules.ps1`, `tests/automated_test.ps1`). Equivalent options: `-Directory`, `-Tools`, `-Yes`, `-Help` for install; `-Root`, `-Tools` for deploy.
- **Git Bash (or MSYS/Cygwin) on Windows:** If you run the Bash `install` or framework Bash tools, they **detect Windows** and automatically delegate to the corresponding PowerShell script (pwsh or powershell). No need to call `.ps1` manually.

## Install command

### Linux / macOS (Bash)

From your client repo root:

```bash
curl -sSL https://raw.githubusercontent.com/cptnfren/localsetup/main/install | bash
```

Note: `sudo curl ... | bash` only elevates curl; install and deploy run as the current user. For a full install as root: `curl -sSL <url> -o /tmp/install.sh && sudo bash /tmp/install.sh`.

Non-interactive (agents/CI):

```bash
curl -sSL .../install | bash -s -- --directory . --tools cursor --yes
```

Multi-platform in one run:

```bash
curl -sSL .../install | bash -s -- --tools cursor,claude-code --yes
```

### Windows (PowerShell)

From your client repo root (after cloning or downloading the repo):

```powershell
# Interactive
.\install.ps1

# Non-interactive
.\install.ps1 -Directory . -Tools cursor -Yes

# Multiple tools
.\install.ps1 -Tools "cursor,claude-code" -Yes
```

If execution policy blocks scripts:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# or one-time bypass:
powershell -ExecutionPolicy Bypass -File .\install.ps1 -Directory . -Tools cursor -Yes
```

## Options

- `--directory PATH` / `-Directory PATH`  - Client repo root (default: .)
- `--tools LIST` / `-Tools LIST`  - Comma-separated: cursor, claude-code, codex, openclaw
- `--yes` / `-Yes`  - Non-interactive (required when using --tools)
- `--help` / `-Help`  - Print usage and exit

## Dependency preflight

Before clone/deploy, both install scripts run a dependency preflight. The list below is the canonical source of truth; when adding or changing runtime dependencies, update the preflight in both `install` (Bash) and `install.ps1` (PowerShell) and this section. See also the repo rule in `.cursor/rules/dependency-preflight.mdc`.

### Canonical dependency list

| Dependency | Required / Recommended | Used by |
|------------|------------------------|---------|
| `git` >= 2.20.0 | Required | Clone and upgrade logic |
| `rg` (ripgrep) | Required on Linux/macOS (Bash install uses it for manifest build). Recommended on Windows. | Bash install manifest; framework/Grep tooling |
| `python` >= 3.10 | Recommended | Framework tools (deploy, verify_context, verify_rules, tests); Python-first policy |
| `pip` | Recommended | Install `_localsetup/requirements.txt` |
| Python: `yaml` (PyYAML>=6.0) | Recommended | YAML parsing for skill index, config, and PRD files |
| Python: `requests` (requests>=2.28) | Recommended | HTTP client used by index refresh and scrub tools |
| Python: `frontmatter` (python-frontmatter>=1.1) | Recommended | YAML frontmatter parsing for skill and PRD markdown files |

Python packages are listed in `_localsetup/requirements.txt`. After install, run:

```bash
python3 -m pip install -r _localsetup/requirements.txt
```

(PowerShell: `python -m pip install -r _localsetup\requirements.txt`.)

To install dependencies automatically during install, add the `--install-deps` / `-InstallDeps` flag:

```bash
# Bash
install --directory . --tools cursor --yes --install-deps

# PowerShell
.\install.ps1 -Directory . -Tools cursor -Yes -InstallDeps
```

Without `--install-deps`, install completes but prints a notice listing missing packages with copy-paste install commands. A `.deps-missing` file is written to `_localsetup/` as a reminder; it is cleared automatically the next time install runs and all packages are present.

If any **required** dependency is missing or too old, install aborts with install hints. If only **recommended** ones are missing, install continues and prints copy-paste command hints for your OS.

## Upgrade-aware install behavior

On re-run, installer upgrades `_localsetup/` using managed-file metadata and conflict-aware rules, then redeploys platform files. Deploy overwrites destination files with updated content; if a destination file is root-owned (e.g. from a previous install run as root), deploy updates the file content and may print a single warning that metadata could not be set (permission denied). The upgrade still succeeds.

- `preserve` (default): keep local customizations when possible
- `force`: overwrite managed files with upstream
- `fail-on-conflict`: stop if local+upstream modified the same managed file

Use with:

- Bash: `--upgrade-policy preserve|force|fail-on-conflict`
- PowerShell: `-UpgradePolicy preserve|force|fail-on-conflict`

## What gets deployed

- **All platforms:** Framework at `_localsetup/` (tools, lib, docs, skills, templates).
- **Per-platform** context loader and skills paths: see [PLATFORM_REGISTRY.md](PLATFORM_REGISTRY.md) (single source of truth; add new platforms there first).

## Framework tools (Bash vs PowerShell)

| Tool | Linux/macOS | Windows |
|------|-------------|---------|
| Install | `./install` or `bash install` | `.\install.ps1` (or run `./install` from Git Bash to auto-detect) |
| Deploy | `./_localsetup/tools/deploy` | `.\_localsetup\tools\deploy.ps1` |
| Verify context | `./_localsetup/tools/verify_context` | `.\_localsetup\tools\verify_context.ps1` |
| Verify rules | `./_localsetup/tools/verify_rules` | `.\_localsetup\tools\verify_rules.ps1` |
| Tests | `./_localsetup/tests/automated_test.sh` | `.\_localsetup\tests\automated_test.ps1` |

Path resolution stays in shell for install/skills: `lib/data_paths.sh` and `lib/data_paths.ps1`. Framework tooling (verify_context, verify_rules, deploy, tests, OS detection) is implemented in Python; the `.sh` and `.ps1` scripts in `tools/`, `tests/`, and `discovery/core/` are thin launchers that invoke the corresponding Python scripts.

## Repo-local

All context and framework state live in the repo. Move or clone the repo and the framework goes with it. No home-directory dependency.

---

<p align="center">
<strong>Author:</strong> <a href="https://github.com/cptnfren">Slavic Kozyuk</a><br>
<strong>Copyright</strong> © 2026 <a href="https://www.cruxexperts.com/">Crux Experts LLC</a> – Innovate, Automate, Dominate.
</p>

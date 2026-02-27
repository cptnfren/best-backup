---
status: ACTIVE
version: 2.8
---

# 🚀 Quickstart

Get Localsetup v2 running in your repo in under a minute. This page covers interactive installation, platform selection, verification, and non-interactive one-liners for CI and automation.

## Prerequisites

- **Required:** `git >= 2.20.0`; on Linux/macOS also `rg` (ripgrep), which the Bash install script uses to build the manifest.
- **Recommended for full framework tooling:** `python >= 3.10`, `pip`, and the Python packages in `_localsetup/requirements.txt` (PyYAML, requests, python-frontmatter). After install, run `python3 -m pip install -r _localsetup/requirements.txt`, or pass `--install-deps` / `-InstallDeps` to have the install script do it automatically.
- **Linux/macOS:** Bash and curl.
- **Windows:** PowerShell 5.1+ or PowerShell Core.
- **Any platform:** Network access to GitHub (or a local clone of this repo).

The installer runs a dependency preflight and prints missing dependencies with install command hints before clone/deploy. Full list: [Multi-platform install – Dependency preflight](MULTI_PLATFORM_INSTALL.md#dependency-preflight).

## 🎯 Interactive install (recommended)

The interactive installer prompts you for directory and platform. No flags required.

### Linux and macOS (Bash)

```bash
curl -sSL https://raw.githubusercontent.com/cptnfren/localsetup/main/install | bash
```

`sudo curl ... | bash` only elevates curl; install and deploy run as the current user. For a full install as root: `curl -sSL <url> -o /tmp/install.sh && sudo bash /tmp/install.sh`.

### Windows (PowerShell)

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/cptnfren/localsetup/main/install.ps1)))
```

The installer asks:

1. **Directory:** Where to create `_localsetup/` (default: current directory).
2. **Platform(s):** Which agent host(s) to deploy context and skills for.

After install completes, it prints a verification command. Run it to confirm context loaded.

## 🔧 Platform IDs

When prompted (or when using `--tools` / `-Tools`), use one or more of these IDs:

| ID | Agent host | Context path | Skills path |
|----|------------|--------------|-------------|
| `cursor` | Cursor IDE | `.cursor/rules/` | `.cursor/skills/localsetup-*/` |
| `claude-code` | Claude Code | `.claude/CLAUDE.md` | `.claude/skills/localsetup-*/` |
| `codex` | OpenAI Codex CLI | `AGENTS.md` (repo root) | `.agents/skills/localsetup-*/` |
| `openclaw` | OpenClaw | [_localsetup/templates/openclaw/OPENCLAW_CONTEXT.md](../templates/openclaw/OPENCLAW_CONTEXT.md) | `skills/localsetup-*/` |

You can deploy to multiple platforms at once by comma-separating: `cursor,claude-code`.

## ✅ Verify installation

After install, run the verification scripts to confirm everything deployed correctly.

### Linux and macOS

```bash
./_localsetup/tools/verify_context
./_localsetup/tools/verify_rules
```

### Windows

```powershell
.\_localsetup\tools\verify_context.ps1
.\_localsetup\tools\verify_rules.ps1
```

Expected output: confirmation that context file exists and skills directory is present.

## ⚡ Non-interactive one-liners

For CI pipelines, automation, or when you already know your platform, use flags to skip prompts. One command per box; pick the one that matches your OS and platform.

### Linux and macOS

#### Cursor

Install into the current directory and deploy context and skills for Cursor only.

```bash
curl -sSL https://raw.githubusercontent.com/cptnfren/localsetup/main/install | bash -s -- --directory . --tools cursor --yes
```

#### Claude Code

Install into the current directory and deploy context and skills for Claude Code only.

```bash
curl -sSL https://raw.githubusercontent.com/cptnfren/localsetup/main/install | bash -s -- --directory . --tools claude-code --yes
```

#### Codex CLI

Install into the current directory and deploy context and skills for OpenAI Codex CLI only.

```bash
curl -sSL https://raw.githubusercontent.com/cptnfren/localsetup/main/install | bash -s -- --directory . --tools codex --yes
```

#### OpenClaw

Install into the current directory and deploy context and skills for OpenClaw only.

```bash
curl -sSL https://raw.githubusercontent.com/cptnfren/localsetup/main/install | bash -s -- --directory . --tools openclaw --yes
```

### Windows (PowerShell)

#### Cursor

Install into the current directory and deploy context and skills for Cursor only.

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/cptnfren/localsetup/main/install.ps1))) -Directory . -Tools cursor -Yes
```

#### Claude Code

Install into the current directory and deploy context and skills for Claude Code only.

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/cptnfren/localsetup/main/install.ps1))) -Directory . -Tools claude-code -Yes
```

#### Codex CLI

Install into the current directory and deploy context and skills for OpenAI Codex CLI only.

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/cptnfren/localsetup/main/install.ps1))) -Directory . -Tools codex -Yes
```

#### OpenClaw

Install into the current directory and deploy context and skills for OpenClaw only.

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/cptnfren/localsetup/main/install.ps1))) -Directory . -Tools openclaw -Yes
```

### From a local clone

If you already have the repo on disk, run from the repo root. One command per box.

#### Linux and macOS

**Cursor**

Install from a local clone into the target directory for Cursor only.

```bash
./install --directory /path/to/your/project --tools cursor --yes
```

**Claude Code**

Install from a local clone into the target directory for Claude Code only.

```bash
./install --directory /path/to/your/project --tools claude-code --yes
```

**Codex CLI**

Install from a local clone into the target directory for Codex CLI only.

```bash
./install --directory /path/to/your/project --tools codex --yes
```

**OpenClaw**

Install from a local clone into the target directory for OpenClaw only.

```bash
./install --directory /path/to/your/project --tools openclaw --yes
```

#### Windows (PowerShell)

**Cursor**

Install from a local clone into the target directory for Cursor only.

```powershell
.\install.ps1 -Directory "C:\path\to\your\project" -Tools cursor -Yes
```

**Claude Code**

Install from a local clone into the target directory for Claude Code only.

```powershell
.\install.ps1 -Directory "C:\path\to\your\project" -Tools claude-code -Yes
```

**Codex CLI**

Install from a local clone into the target directory for Codex CLI only.

```powershell
.\install.ps1 -Directory "C:\path\to\your\project" -Tools codex -Yes
```

**OpenClaw**

Install from a local clone into the target directory for OpenClaw only.

```powershell
.\install.ps1 -Directory "C:\path\to\your\project" -Tools openclaw -Yes
```

## 🔄 Updating

Re-run the install command with the same `--directory` and `--tools` (or `-Directory` and `-Tools` on Windows). Two policies:

**Update with default policy (preserve local customizations)**

Use this when you have customized context or rules and want to keep them. The installer merges framework updates but does not overwrite your local changes when it can avoid it.

```bash
./install --directory . --tools cursor --yes --upgrade-policy preserve
```

**Update and fail if there are conflicts**

Use this in CI or when you want the run to exit with an error if the framework and your local changes conflict, instead of overwriting.

```bash
./install --directory . --tools cursor --yes --upgrade-policy fail-on-conflict
```

On Windows (PowerShell), use `.\install.ps1 -Directory . -Tools cursor -Yes -UpgradePolicy preserve` or `-UpgradePolicy FailOnConflict` for the same behavior.

## If dependencies are missing

If preflight reports missing **ripgrep (rg)** on Linux/macOS, install it or install will abort:

```bash
# Debian/Ubuntu
sudo apt-get install -y ripgrep
# Fedora/RHEL: sudo dnf install -y ripgrep
# Arch: sudo pacman -S --needed ripgrep
# macOS: brew install ripgrep
```

If preflight reports missing **Python/pip** or any Python modules, install and then install the framework requirements:

```bash
# Debian/Ubuntu
sudo apt-get update && sudo apt-get install -y python3 python3-pip python3-yaml

# Fedora/RHEL
sudo dnf install -y python3 python3-pip python3-pyyaml

# Arch
sudo pacman -S --needed python python-pip python-yaml

# Any: install all Python packages at once from repo root
python3 -m pip install -r _localsetup/requirements.txt
```

```powershell
# Windows
winget install Python.Python.3.12
py -m pip install -r _localsetup\requirements.txt
```

Alternatively, re-run install with `--install-deps` (Bash) or `-InstallDeps` (PowerShell) to have the script run `pip install` automatically after deploying the framework.

## 📖 Next steps

- [Features](FEATURES.md) - full capability list
- [Shipped skills catalog](SKILLS.md) - all shipped skills
- [Platform registry](PLATFORM_REGISTRY.md) - canonical platform definitions
- [Multi-platform install](MULTI_PLATFORM_INSTALL.md) - detailed cross-platform docs

---

<p align="center">
<strong>Author:</strong> <a href="https://github.com/cptnfren">Slavic Kozyuk</a><br>
<strong>Copyright</strong> © 2026 <a href="https://www.cruxexperts.com/">Crux Experts LLC</a> – Innovate, Automate, Dominate.
</p>

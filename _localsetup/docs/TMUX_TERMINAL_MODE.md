---
status: ACTIVE
version: 2.8
---

# Tmux-default terminal mode

A toggleable framework feature that makes new terminal sessions open inside a named tmux session by default, and enforces a mandatory tmux + sudo gate rule for all agent host operations.

Enable it once per machine. Disable it any time with a single command. No manual file editing required.

---

## Why this exists

Without this mode, terminal sessions open as plain bash. An agent running host commands has no shared view with the operator, sudo prompts are invisible, and long-running commands are lost if the connection drops.

This mode fixes that in two layers:

- **Layer 1:** Automatically opens new terminals inside a tmux session (IDE profile or shell auto-attach, depending on mode).
- **Layer 2:** Injects a mandatory agent rule into your rules file so agents always use the tmux workflow and the sudo gate.

---

## Modes

Choose the mode that matches how you work on this machine:

| Mode | Use when | What it configures |
|---|---|---|
| `--mode ide` (default) | Using Cursor or VS Code Remote as your primary interface | IDE terminal profile (Layer 1a) + agent rule (Layer 2) |
| `--mode shell` | SSH sessions, servers without an IDE, CI, plain terminal | Shell RC auto-attach (Layer 1b) + agent rule (Layer 2) |

Both modes configure the same agent rule (Layer 2) and tmux_ops tool (Layer 3). The difference is only in how Layer 1 launches tmux.

---

## Quick start

```bash
# IDE mode (Cursor/VS Code Remote):
./_localsetup/tools/tmux_terminal_mode enable

# Shell mode (SSH/plain terminal):
./_localsetup/tools/tmux_terminal_mode enable --mode shell

# Check status:
./_localsetup/tools/tmux_terminal_mode status

# Disable:
./_localsetup/tools/tmux_terminal_mode disable
```

---

## Enable

```
./_localsetup/tools/tmux_terminal_mode enable [--mode {ide,shell}] [--session NAME]
    [--settings-file PATH] [--shell-rc PATH] [--rules-file PATH] [--dry-run]
```

### Flags

| Flag | Default | Description |
|---|---|---|
| `--mode {ide,shell}` | `ide` | Which Layer 1 variant to apply |
| `--session NAME` | `ops` | tmux session name written into profile/RC/rule |
| `--settings-file PATH` | auto-detected | IDE settings.json path (ide mode only) |
| `--shell-rc PATH` | `~/.bashrc` (Linux) / `~/.bash_profile` (macOS) | Shell RC file (shell mode only) |
| `--rules-file PATH` | `.cursor/rules/operator-memory.mdc` | Agent rules file |
| `--dry-run` | off | Print what would change; modify nothing |

### What enable does

**IDE mode (Layer 1a):**

Auto-detects the settings file in this order:

1. `~/.cursor-server/data/Machine/settings.json` (Cursor Remote SSH, Linux)
2. `~/.vscode-server/data/Machine/settings.json` (VS Code Remote SSH, Linux)
3. `~/Library/Application Support/Cursor/User/settings.json` (Cursor Desktop, macOS)
4. `~/Library/Application Support/Code/User/settings.json` (VS Code Desktop, macOS)

Adds a `tmux-session` terminal profile and sets it as the default. The original settings file is backed up as `<file>.tmux-mode.bak`. After enable, restart the IDE terminal panel for the new profile to appear.

**Shell mode (Layer 1b):**

Appends a sentinel-wrapped block to your RC file:

```bash
# BEGIN tmux-default-terminal-mode
# Auto-attach to tmux session if not already inside tmux.
if [ -z "$TMUX" ] && [ -n "$PS1" ]; then
  exec tmux new-session -A -s ops
fi
# END tmux-default-terminal-mode
```

The `exec` replaces the shell process so there is no double-shell overhead. The guards ensure this only fires for interactive, non-tmux sessions.

> **Important:** Shell mode uses `exec tmux`, which means opening a new terminal is the only way to activate it, and `disable` + opening a new terminal is the only clean way back to a plain shell.

**Both modes (Layer 2):**

Appends a sentinel-wrapped mandatory tmux + sudo gate rule to the rules file. Agents following this rule will use `tmux_ops pick`, `tmux_ops probe`, and `tmux_ops send` for every host command.

### Idempotency

Running enable twice in either mode is safe. If the sentinel blocks are already present, they are not duplicated.

---

## Disable

```
./_localsetup/tools/tmux_terminal_mode disable [--mode {ide,shell}]
    [--settings-file PATH] [--shell-rc PATH] [--rules-file PATH] [--dry-run]
```

Removes the Layer 1 variant for the specified mode and Layer 2 from the rules file.

- If a `.tmux-mode.bak` backup exists, it is restored and the backup is deleted.
- If no backup exists, only the sentinel block is removed; everything else in the file is untouched.
- If neither the sentinel nor a backup is found, disable exits 0 with "nothing to do."

After disabling IDE mode: restart the IDE terminal panel.
After disabling shell mode: open a new terminal to get a plain shell.

---

## Status

```
./_localsetup/tools/tmux_terminal_mode status [--settings-file PATH]
    [--shell-rc PATH] [--rules-file PATH]
```

Reports all layers unconditionally regardless of which mode was used at enable time. Example output:

```
tmux-default terminal mode status
  Mode detected:           ide
  Session name:            ops
  Layer 1a (IDE profile):  ACTIVE   [tmux-session → ops, settings: ~/.cursor-server/...]
  Layer 1b (shell RC):     INACTIVE
  Layer 2  (agent rule):   ACTIVE   [rules: .cursor/rules/operator-memory.mdc]
  Layer 3  (tmux_ops):     PRESENT  [_localsetup/tools/tmux_ops]
```

Partial or mixed states (e.g. Layer 1a active but Layer 2 missing) are reported as-is so you can diagnose and re-run enable for the missing layer.

---

## Manual rollback

If the script is unavailable, revert manually:

**IDE mode (Layer 1a):**

```bash
# Option A: restore backup
cp ~/.cursor-server/data/Machine/settings.json.tmux-mode.bak \
   ~/.cursor-server/data/Machine/settings.json

# Option B: remove the two keys from settings.json with any editor:
#   "terminal.integrated.profiles.linux" -> remove the "tmux-session" entry
#   "terminal.integrated.defaultProfile.linux" -> remove the key
```

**Shell mode (Layer 1b):**

```bash
# Option A: restore backup
cp ~/.bashrc.tmux-mode.bak ~/.bashrc

# Option B: remove lines between (and including) these markers:
# BEGIN tmux-default-terminal-mode
# END tmux-default-terminal-mode
```

**Both modes (Layer 2 - agent rule):**

```bash
# Remove lines between (and including):
# BEGIN tmux-default-terminal-mode
# END tmux-default-terminal-mode
# from .cursor/rules/operator-memory.mdc (or whichever --rules-file you used)
```

All of these require only a text editor or `cp`.

---

## Changing the session name

The session name is written into the Layer 1 block and the Layer 2 rule at enable time. To change it:

```bash
./_localsetup/tools/tmux_terminal_mode disable --mode <your-mode>
./_localsetup/tools/tmux_terminal_mode enable --mode <your-mode> --session <new-name>
```

---

## Layer 3: tmux_ops

Layer 3 is the `_localsetup/tools/tmux_ops` tool already present in the framework. Enable does not modify it. The agent rule (Layer 2) references it for pick, probe, and send operations. Status reports whether the tool is present.

For full tmux_ops documentation see the `localsetup-tmux-shared-session-workflow` skill and `ops/tmux-ops-remote.md`.

---

<p align="center">
<strong>Author:</strong> <a href="https://github.com/cptnfren">Slavic Kozyuk</a><br>
<strong>Copyright</strong> © 2026 <a href="https://www.cruxexperts.com/">Crux Experts LLC</a> – Innovate, Automate, Dominate.
</p>

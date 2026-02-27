# Tmux ops tool: remote (VMs, SSH, Docker)

**Purpose:** Use the tmux_ops workflow when the tmux server runs on a different host than where you run the command (e.g. Cursor on laptop, tmux on a VM or remote server).

## Config

- **REMOTE_TMUX_HOST** – Hostname or IP of the machine where tmux runs. When set, the `tmux_ops` wrapper runs the Python tool over SSH on that host and returns the same JSON.
- **REMOTE_TMUX_CWD** – (Optional) Repo path on the remote. Default: `/opt/devzone/devops`.

## Usage

From repo root (with Cursor/agent on your laptop):

```bash
export REMOTE_TMUX_HOST=sh0t
./_localsetup/tools/tmux_ops pick
./_localsetup/tools/tmux_ops probe -t ops
```

When REMOTE_TMUX_HOST is set, run commands via the same wrapper so the pylon-guard delay runs on the remote side:

```bash
./_localsetup/tools/tmux_ops send -t ops 'sudo apt update'
./_localsetup/tools/tmux_ops send -t ops --wait 'echo done'        # wait for idle
./_localsetup/tools/tmux_ops wait -t ops --timeout 120              # standalone wait for long ops
```

Do not use raw `tmux send-keys` over SSH; use `tmux_ops send` (and `wait`) as usual so the tool runs on the remote.

Log paths and session names are the same; they refer to paths and sessions on the remote host.

## When not to set it

If you use Cursor Remote SSH and the agent runs on the same host as tmux, do **not** set REMOTE_TMUX_HOST. Run `tmux_ops` and send commands directly.

## Reference

- Skill: **localsetup-tmux-shared-session-workflow**
- Tool: `_localsetup/tools/tmux_ops` (pick, probe -t SESSION, send -t SESSION [--wait] 'cmd', wait -t SESSION [--timeout N])

---
status: ACTIVE
version: 2.8
---

# Workflow and module registry (Localsetup v2)

**Purpose:** Registry of named workflows and when to use them; impact review when required.

## Core

| Name | Description | When to use | Impact review |
|------|-------------|-------------|---------------|
| Master rule / context | Always-loaded framework context | Always | No |
| Skills index | List of skills and when to use | When discovering which skill to load | No |

## Workflows

| Name | Description | When to use | Impact review |
|------|-------------|-------------|---------------|
| Decision tree | One Q per turn, 4 options A-D, preferred + rationale | User says "decision tree" or "reverse prompt" | No |
| Agent Q (queue) | Process specs in .agent/queue/; implement, status, outcome | User says "process PRDs" or "run batch from PRD folder" | Yes if destructive |
| Umbrella workflow | Multi-phase single kickoff; named workflows | User invokes by name (e.g. "execute umbrella workflow X") | Yes for big/destructive |
| Manual execution (lazy admin) | Human-in-the-loop; three-block format; info-gather before destructive | Sudo, confirmation, manual steps | No (protocol is guardrail) |
| Tmux shared session | All server ops in tmux via tmux_ops (pick, probe, send, wait); pylon-guard delay between sends; adaptive idle polling (`send --wait` or standalone `wait`); human can attach; sudo gate via probe; REMOTE_TMUX_HOST for remote/VMs | Server commands, deployments, tmux, human-in-the-loop | No (skill defines gate) |
| Framework audit | Run doc/link/skill matrix/version checks; output user-specified path; optional `--deep` (Deep Analysis: derive invocations from SKILL.md and script `--help`, run in sandbox, summary JSON + sidecar tarball; requires output path) | User says "run audit", "run framework audit", or before release | No |
| Public skill index maintenance | Refresh index from registries then scrub: (1) `refresh_public_skill_index.py`, (2) `skill_index_scrub.py --skip-url-check`, (3) `skill_index_scrub.py --skip-url-check --fix`. Full URL check optional (add `--workers 20`, omit `--skip-url-check`) before release. | User says "refresh skills", "update public skill index", "refresh and scrub", or "scrub the index"; also runs automatically after any index refresh | No |
| Tmux-default terminal mode | Enable/disable/status via `_localsetup/tools/tmux_terminal_mode`. `enable --mode ide` adds Cursor/VS Code terminal profile; `enable --mode shell` appends auto-attach to RC file. Both modes inject the mandatory agent ops rule. `disable` restores backups. Idempotent. See [TMUX_TERMINAL_MODE.md](TMUX_TERMINAL_MODE.md). | User says "enable tmux mode", "tmux terminal mode", "set up tmux default terminal", "disable tmux mode", or "tmux terminal status"; or when setting up a new machine for ops work | No |

Release and publish (including version bump) are maintained in a separate maintainer repository; not documented here.

## Usage

- **Agents:** For workflows marked impact review, present impact summary and get user confirmation before proceeding.
- **Skills:** Load the matching skill (localsetup-decision-tree-workflow, localsetup-agentic-prd-batch, localsetup-agentic-umbrella-queue, localsetup-tmux-shared-session-workflow, etc.) when the task matches.
- **Tmux/sudo:** See skill localsetup-tmux-shared-session-workflow and tool `_localsetup/tools/tmux_ops`: pick session (idle = prompt on current line), probe (ready vs password_required), send with pylon-guard delay, `send --wait` for idle confirmation, standalone `wait --timeout N` for long ops. Use tmux_ops send for every step; never use raw tmux send-keys. When REMOTE_TMUX_HOST is set, wrapper runs tool over SSH. Doc: [ops/tmux-ops-remote.md](ops/tmux-ops-remote.md). Re-prompt only when probe returns password_required.
- **Public skill index maintenance:** When user says "refresh skills", "update public skill index", "refresh and scrub", or "scrub the index", run the three-step sequence via `localsetup-skill-discovery`: refresh → scrub dry-run → scrub fix. See [SKILL_DISCOVERY.md](SKILL_DISCOVERY.md) "Post-refresh scrub" for the full command sequence. The scrub also runs automatically whenever an index refresh is triggered through the skill-discovery workflow.
- **Tmux-default terminal mode:** When user says "enable tmux mode", "tmux terminal mode", "set up tmux default terminal", "disable tmux mode", or "tmux terminal status", run the appropriate sub-command: `_localsetup/tools/tmux_terminal_mode enable [--mode ide|shell] [--session NAME]`, `disable`, or `status`. See [TMUX_TERMINAL_MODE.md](TMUX_TERMINAL_MODE.md).

---

<p align="center">
<strong>Author:</strong> <a href="https://github.com/cptnfren">Slavic Kozyuk</a><br>
<strong>Copyright</strong> © 2026 <a href="https://www.cruxexperts.com/">Crux Experts LLC</a> – Innovate, Automate, Dominate.
</p>

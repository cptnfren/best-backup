---
status: ACTIVE
version: 2.8
---

# ⚡ Features

This is the complete public feature catalog for Localsetup v2. The main README highlights the top 10; this page covers everything.

## 📊 Generated facts

<!-- facts-block:start -->
- Current version: `2.8.0`
- Supported platforms: `cursor, claude-code, codex, openclaw`
- Shipped skills: `39`
- Source: `_localsetup/docs/_generated/facts.json`
<!-- facts-block:end -->

---

## 📦 Engine and deployment

| Capability | Description |
|---|---|
| **Repo-local engine** | The entire framework lives at `_localsetup/` inside your project. Clone or move the repo and everything travels together. No home-directory state, no cloud dependency. |
| **Cross-platform installers** | Bash installer for Linux and macOS; PowerShell installer for Windows. Both support interactive and non-interactive modes. |
| **Multi-host deployment** | Deploy context and skills to Cursor, Claude Code, OpenAI Codex CLI, or OpenClaw from a single install command. |
| **Idempotent updates** | Re-running install updates the framework (via git pull) and redeploys context. Safe to run repeatedly. Deploy can overwrite root-owned destination files (content is updated; a metadata warning may appear). |
| **Platform registry** | A single Markdown table ([PLATFORM_REGISTRY.md](PLATFORM_REGISTRY.md)) defines every supported platform ID, context path, and skills path. Add new platforms by editing one file. |

---

## 🛠️ Skills and interoperability

| Capability | Description |
|---|---|
| **Agent Skills spec compliance** | All shipped skills follow the [Agent Skills specification](https://agentskills.io/specification). Import skills from Anthropic's repo or any spec-compliant source. |
| **Shipped skills** | Debugging, TDD, PR review, git recovery, Linux triage, Linux patching, Ansible orchestration, codebase navigation (agentlens), tmux ops (pick/probe/send), system-info, cron-orchestrator, PRD batching, decision trees, humanizer, and more. See [SKILLS.md](SKILLS.md) for the full catalog. |
| **Skill importing** | Import external skills from a GitHub URL or local path. The importer discovers, validates, runs a heuristic security screen, and summarizes each skill before you decide to add it. |
| **Skill discovery** | Maintain a public skill registry ([PUBLIC_SKILL_REGISTRY.urls](PUBLIC_SKILL_REGISTRY.urls)) and index ([PUBLIC_SKILL_INDEX.yaml](PUBLIC_SKILL_INDEX.yaml)). Get recommendations for similar public skills when creating or importing. The discovery workflow includes a mandatory post-refresh scrub step that catches dead URLs, stub/placeholder descriptions, and schema gaps automatically. |
| **Skill version metadata** | Each `SKILL.md` carries a `metadata.version` field. The commit hook auto-increments patch version on staged skill changes so skill docs stay accurate. |
| **Skill normalization** | Normalize imported or in-tree skills: Phase 1 (documents) offers a choice when the skill is platform-specific (keep as is, keep platform-specific but normalized, or fully normalize); Phase 2 (tooling) rewrites bundled scripts to the framework standard unless the user requests an exception. Use the `localsetup-skill-normalizer` skill or run during import. |

---

## 🔄 Workflow and quality controls

| Capability | Description |
|---|---|
| **Decision tree workflow** | A reverse-prompt process where the agent asks one question at a time with four options, a preferred choice, and rationale. Builds context before implementation. |
| **PRD batch workflow** | Process specs from `.agent/queue/`; implement per spec, update status, write outcomes, and reference the PRD schema. |
| **Framework compliance** | Checklist-based workflow for framework-safe modifications: certainty assessment, context load, document status, testing, git checkpoints. |
| **Script and docs quality** | Markdown encoding standards, script generation quality rules, file creation discipline, and documentation discipline enforced by the `localsetup-script-and-docs-quality` skill. |
| **Human-in-the-loop ops** | The tmux shared-session workflow uses the tmux_ops tool (pick, probe, send, wait). Pylon-guard delay prevents command racing; `send --wait` or standalone `wait --timeout N` provides adaptive idle polling. Human can attach and provide sudo; agent captures output via log files. Supports REMOTE_TMUX_HOST for VMs/remote/Docker. See [ops/tmux-ops-remote.md](ops/tmux-ops-remote.md). Use for privileged or risky operations. |
| **Tmux-default terminal mode** | Toggleable feature (`tmux_terminal_mode enable/disable/status`) that makes new terminals open inside a tmux session automatically and injects a mandatory tmux + sudo gate rule for agents. Two modes: `--mode ide` (Cursor/VS Code terminal profile) and `--mode shell` (bashrc/bash_profile auto-attach). Single command to enable or disable; backups created before any file is modified; idempotent. See [TMUX_TERMINAL_MODE.md](TMUX_TERMINAL_MODE.md). |
| **Arbiter workflow** | Push decisions to Arbiter Zebu for async human review when you need approval before proceeding. |
| **Framework audit** | Single entrypoint runs doc checks, link checks, skill matrix (discovery + sandbox smoke), version/facts, and optional Deep Analysis (`--deep`): derives invocations from SKILL.md and script `--help`, runs in sandbox, writes summary JSON and sidecar tarball. Output only to user-specified path; no in-repo default. See [WORKFLOW_REGISTRY.md](WORKFLOW_REGISTRY.md) and skill `localsetup-framework-audit`. |
| **Public skill index maintenance** | Named workflow (trigger: "refresh skills", "refresh and scrub", "update public skill index") that runs the full three-step sequence: (1) refresh from registries, (2) dry-run scrub to detect stubs and dead URLs, (3) apply fixes. Implemented by `refresh_public_skill_index.py` and `skill_index_scrub.py`. See [SKILL_DISCOVERY.md](SKILL_DISCOVERY.md). |

---

## 🔢 Git, versioning, and traceability

| Capability | Description |
|---|---|
| **Conventional commit bumping** | Version bump is inferred from commit messages (feat: → minor, fix:/docs: → patch). Framework version and docs are maintained by repo maintainers; see [docs/VERSIONING.md](../../docs/VERSIONING.md). |
| **README and docs sync** | Version values are synchronized to `README.md`, `_localsetup/README.md`, and YAML frontmatter in `_localsetup/docs/*.md` and `docs/*.md`. |
| **Attribution guardrails** | The commit hook strips `Co-authored-by` trailers for AI agents and bots. Only humans appear in commit history. |
| **Git traceability model** | PRDs, specs, and outcomes can reference git commit hashes for audit. See [GIT_TRACEABILITY.md](GIT_TRACEABILITY.md). |
| **Maintenance workflow** | Framework version and docs are maintained by the repository maintainers. See [docs/VERSIONING.md](../../docs/VERSIONING.md) for how version is defined and displayed. |
| **Skill metadata patching** | Skill `metadata.version` in SKILL.md is updated by maintainers when skills change; see [AGENT_SKILLS_COMPLIANCE.md](AGENT_SKILLS_COMPLIANCE.md). |

---

## 🖥️ Developer and ops skills

These skills ship with the framework and are ready to use immediately.

| Skill | Purpose |
|---|---|
| `localsetup-debug-pro` | Systematic debugging methodology with language-specific commands (Node, Python, Swift, network, git bisect). |
| `localsetup-test-runner` | Write and run tests across frameworks: pytest, Jest, Vitest, XCTest, Playwright. TDD workflow and coverage patterns. |
| `localsetup-tdd-guide` | Test-driven development workflow with test generation, coverage analysis, and red-green-refactor guidance. |
| `localsetup-pr-reviewer` | Automated GitHub PR review with diff analysis, lint integration, and structured reports. Requires `gh` CLI. |
| `localsetup-git-workflows` | Advanced git operations: rebase, bisect, worktree, reflog, subtree, conflict resolution, cherry-pick, monorepo patterns. |
| `localsetup-unfuck-my-git-state` | Diagnose and recover broken Git state: detached HEAD, phantom worktrees, missing refs, orphaned entries. |
| `localsetup-linux-service-triage` | Diagnose common Linux service issues using logs, systemd/PM2, file permissions, Nginx checks, DNS sanity checks. |
| `localsetup-linux-patcher` | Automated server patching and Docker container updates across Ubuntu, Debian, RHEL, AlmaLinux, Rocky, CentOS, Amazon Linux, SUSE. |
| `localsetup-ansible-skill` | Ansible playbook-driven provisioning, configuration management, and multi-host orchestration. Includes example playbooks. |
| `localsetup-agentlens` | Codebase navigation using agentlens hierarchy (INDEX.md, modules, outline, memory); explore projects, find modules/symbols, TODOs. |
| `localsetup-mcp-builder` | Guide for creating high-quality MCP servers that enable LLMs to interact with external services. Python and Node/TypeScript. |
| `localsetup-system-info` | Quick system diagnostics: CPU, memory, disk, uptime. Capture server baseline or host layout for further operations. |
| `localsetup-cron-orchestrator` | Manage cron from a repo-local manifest: time triggers, on-boot-with-delay, sequenced tasks; create, remove, reorder, install. |
| `localsetup-cloudflare-dns` | Manage Cloudflare DNS records (list, create, modify, delete) and run zone surveys via flarectl; Python wrapper, no shell dependencies. |
| `localsetup-npm-management` | Manage Nginx Proxy Manager proxy hosts via REST API using the native Python client; covers create, modify, diagnose, remove, cleanup, and backup workflows; coordinates Docker + NPM deployments. |

---

## 🤖 Workflow and meta skills

| Skill | Purpose |
|---|---|
| `localsetup-decision-tree-workflow` | Reverse-prompt process: one question at a time, four options, preferred choice, rationale. |
| `localsetup-agentic-prd-batch` | Process PRDs from queue; implement per spec; update status; write outcome. |
| `localsetup-agentic-umbrella-queue` | Named workflows with impact summary and user confirmation before big/destructive runs. |
| `localsetup-framework-compliance` | Pre-task workflow, certainty assessment, context load, document status, testing, git checkpoints. |
| `localsetup-automatic-versioning` | Manage VERSION, conventional commits, sync to READMEs and docs; version maintained by repo maintainers. |
| `localsetup-github-publishing-workflow` | Publishing checklist: doc structure, licensing, PII/secrets scrub, repo readiness. |
| `localsetup-tmux-shared-session-workflow` | Human-in-the-loop ops via tmux_ops (pick/probe/send/wait); sudo gate on probe; adaptive idle polling (`send --wait` or `wait --timeout N`); REMOTE_TMUX_HOST for remote. |
| `localsetup-arbiter` | Push decisions to Arbiter Zebu for async human review. |
| `localsetup-backlog-and-reminders` | Record deferred ideas, to-dos, reminders; show due/overdue on session start. |
| `localsetup-task-skill-matcher` | Match tasks to installed skills; recommend top matches; single or batch flow. |
| `localsetup-framework-audit` | Run doc/link/skill matrix/version checks before release; optional `--deep` (Deep Analysis: derive invocations, run in sandbox, summary JSON + tarball); output to user path only. |

---

## ✍️ Quality and communication skills

| Skill | Purpose |
|---|---|
| `localsetup-humanizer` | Remove AI-writing patterns from text based on Wikipedia's "Signs of AI writing" guide. |
| `localsetup-script-and-docs-quality` | Markdown/encoding standards, script quality, file and docs discipline. |
| `localsetup-communication-and-tools` | Communication guidelines, tool selection, periodic context updates. |
| `localsetup-public-repo-identity` | Public identity rules for README and published repos. |
| `localsetup-receiving-code-review` | Verify before implementing code review feedback; avoid blind agreement. |

---

## 🔐 Security and skill vetting

| Skill | Purpose |
|---|---|
| `localsetup-safety-and-backup` | Conservative security, backup management, temp files, firewall rules. |
| `localsetup-skill-vetter` | Security-first vetting for external skills before install. |
| `localsetup-skill-importer` | Import from URL or path with discovery, validation, and security screening. |
| `localsetup-skill-creator` | Create Agent Skills-compliant skills; import from Anthropic or elsewhere; export yours. |
| `localsetup-skill-discovery` | Discover public skills from registries; recommend similar; in-depth summary. |
| `localsetup-skill-normalizer` | Normalize skills: Phase 1 (documents, with platform choice when platform-specific); Phase 2 (tooling rewrite to framework standard, or exception). |

---

## 📖 Next steps

- [Shipped skills catalog](SKILLS.md) - generated list of all shipped skills with descriptions and versions
- [Platform registry](PLATFORM_REGISTRY.md) - canonical platform definitions
- [Workflow registry](WORKFLOW_REGISTRY.md) - named workflows and when to use them
- [Agentic design index](AGENTIC_DESIGN_INDEX.md) - index of agentic design docs

---

<p align="center">
<strong>Author:</strong> <a href="https://github.com/cptnfren">Slavic Kozyuk</a><br>
<strong>Copyright</strong> © 2026 <a href="https://www.cruxexperts.com/">Crux Experts LLC</a> – Innovate, Automate, Dominate.
</p>

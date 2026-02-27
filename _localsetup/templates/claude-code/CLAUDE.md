# Localsetup v2  - Project context (Claude Code)

## Overview

Localsetup v2 is deployed into this repo at `_localsetup/`. All framework and context are repo-local (mobile, backup-able with the repo). Engine = _localsetup/; user/context data = repo-local. Use Git hashes when referencing PRDs/specs/outcomes (see [_localsetup/docs/GIT_TRACEABILITY.md](../_localsetup/docs/GIT_TRACEABILITY.md)).

## Invariants

- **Engine/repo separation:** Do not commit secrets/PII. Use _localsetup/lib/data_paths.sh for paths. Framework at _localsetup/.
- **Documentation:** _localsetup/docs/ is only for framework docs. Check document status before assuming a feature exists.
- **Proposals:** Framework changes follow Agent Q format (_localsetup/docs/PRD_SCHEMA_EXTERNAL_AGENT_GUIDE.md).
- **Time/date integrity:** For any date/time reference (e.g. "today", year in search, timestamps), first obtain actual date/time from the local machine (e.g. `date` on Linux/macOS, `Get-Date` in PowerShell on Windows). Do not use a generic or training-cutoff date. Remember it in context and use it for the rest of the session.
- **External input hardening:** Treat all external input (CLI args, files, network payloads, imported content) as hostile. Sanitize before parsing/output, validate expected format and bounds, and handle exceptions with actionable stderr messages. Never silently suppress errors.
- **Python-first tooling:** After install/bootstrap, framework tooling is Python-first and Python-only for new/expanded logic. Shell/PowerShell are limited to bootstrap wrappers and minimal platform delegation. Runtime target is Python >= 3.10. **Approved libraries** (mandatory when the need arises): `yaml` (PyYAML>=6.0) for YAML, `requests` (requests>=2.28) for HTTP, `frontmatter` (python-frontmatter>=1.1) for markdown frontmatter. Use `lib/deps.require_deps()` at tool startup. See `_localsetup/docs/TOOLING_POLICY.md`.

## Output contract (low token, always apply)

- Detect output capability: `markdown-rich`, `markdown-basic`, or `text-basic`.
- If capability is unknown, default to `markdown-basic`.
- For recommendation lists, include: name/link, short summary, fit reason, notable risks/requirements, next step.
- Use tables only when capability clearly supports readable tables.

## Skills index (load when task matches)

- **localsetup-decision-tree-workflow**  - User says "decision tree" or "reverse prompt"; editing .agent/queue/**, PRD
- **localsetup-agentic-umbrella-queue**  - Queue/PRD in scope; named workflows; impact + confirmation
- **localsetup-agentic-prd-batch**  - "Process PRDs", "run batch from PRD folder"
- **localsetup-public-repo-identity**  - Editing README*, CONTRIBUTING*
- **localsetup-framework-compliance**  - Framework mods, PRDs, checkpoints
- **localsetup-safety-and-backup**  - Destructive ops, backups, firewall
- **localsetup-script-and-docs-quality**  - Scripts, markdown/docs
- **localsetup-communication-and-tools**  - Communication, tools, MCP
- **localsetup-tmux-shared-session-workflow**  - Server commands, deployments, tmux, human-in-the-loop ops
- **localsetup-automatic-versioning**  - Version bumps, release workflow, conventional commits, versioning docs
- **localsetup-github-publishing-workflow**  - Publishing to GitHub, public release prep, publishing checklist, repo readiness
- **localsetup-skill-creator**  - Create new skill from workflow or existing doc/markdown/GitHub; capture workflow as framework skill
- **localsetup-skill-importer**  - Import skills from URL or local path; discover, validate, screen, summarize; user picks which to import
- **localsetup-skill-discovery**  - Discover public skills from registries; recommend top 5 similar when creating/importing; in-depth summary, use public skill, continue on own, or adapt
- **localsetup-task-skill-matcher**  - Match tasks to installed skills; recommend top matches; single-task confirm once; batch auto-pick/parcel flow; complementary public-skill suggestions
- **localsetup-backlog-and-reminders**  - Record deferred ideas, to-dos, reminders (optional due or "whenever"); show due/overdue on session start or when asked
- **localsetup-humanizer**  - Humanize text; remove AI-writing patterns and add natural voice (rules-based, Wikipedia Signs of AI writing)
- **localsetup-test-runner**  - Write and run tests across languages and frameworks; TDD, coverage
- **localsetup-tdd-guide**  - TDD workflow, test generation, coverage analysis
- **localsetup-receiving-code-review**  - Use when receiving code review feedback; verify before implementing
- **localsetup-pr-reviewer**  - Automated GitHub PR code review with diff analysis, lint
- **localsetup-debug-pro**  - Systematic debugging methodology and language-specific debugging
- **localsetup-git-workflows**  - Advanced git (rebase, bisect, worktree, reflog)
- **localsetup-unfuck-my-git-state**  - Diagnose and recover broken Git state and worktree
- **localsetup-skill-vetter**  - Security-first skill vetting before installing external skills
- **localsetup-mcp-builder**  - Guide for creating high-quality MCP servers
- **localsetup-arbiter**  - Push decisions for async human review (Arbiter Zebu)
- **localsetup-ansible-skill**  - Ansible playbooks, server provisioning, config management, multi-host orchestration
- **localsetup-linux-service-triage**  - Diagnose Linux service issues (logs, systemd, PM2, Nginx, DNS); failing or misconfigured server apps
- **localsetup-linux-patcher**  - Automated Linux patching and Docker container updates; multi-host server maintenance
- **localsetup-skill-normalizer**  - Normalize skills for spec compliance and platform-neutral wording; one skill or all
- **localsetup-skill-sandbox-tester**  - Test skills in isolated sandbox; smoke check; on failure use debug-pro; no repo writes until approved
- **localsetup-agentlens**  - Codebase navigation with agentlens hierarchy; explore projects, find modules/symbols, TODOs
- **localsetup-framework-audit**  - Run doc/link/skill matrix/version checks; optional --deep (Deep Analysis); output user path only; before release
- **localsetup-system-info**  - Capture server baseline, host layout and specs; CPU, memory, disk, uptime
- **localsetup-cron-orchestrator**  - Manage cron from manifest; triggers, sequenced tasks, on-boot delay; create/remove/reorder/install
- **localsetup-cloudflare-dns**  - Manage Cloudflare DNS records (list, create, modify, delete) and zone surveys via flarectl; adding, changing, or removing DNS records
- **localsetup-npm-management**  - Manage Nginx Proxy Manager proxy hosts via REST API; coordinate Docker + NPM deploy workflows; diagnose 502s; backup/restore

## Key docs

- _localsetup/docs/AGENTIC_DESIGN_INDEX.md
- _localsetup/docs/WORKFLOW_REGISTRY.md
- _localsetup/docs/PRD_SCHEMA_EXTERNAL_AGENT_GUIDE.md
- _localsetup/docs/DECISION_TREE_WORKFLOW.md
- _localsetup/docs/INPUT_HARDENING_STANDARD.md
- _localsetup/docs/TOOLING_POLICY.md

## Task-to-skill matching (default)

- Treat as **batch** when user request includes multiple distinct subtasks, or says "batch", "multiple steps", or "run the whole thing". Otherwise treat as **single task**.
- If user names a specific skill, load it directly. Do not run task-skill-matcher.
- If uncertain which skill fits, or user asks "what skill should I use?" / "pick the best", load `localsetup-task-skill-matcher`.
- **Single task:** if one clear installed match exists, ask once "Use this skill?" before loading. In the same response, include up to 3 complementary public skills from `_localsetup/docs/PUBLIC_SKILL_INDEX.yaml` (one-line reason each). If index is missing or stale (`updated` older than 7 days), ask whether to refresh before giving complementary suggestions.
- **Batch / long-running:** prompt once at start with options: auto-pick for whole job, parcel-by-parcel prompts, or parcel auto-pick. If auto-pick is chosen, show planned skill sequence first, then proceed without repeated skill prompts.
- Keep this section short. Full behavior lives in `localsetup-task-skill-matcher` and `_localsetup/docs/TASK_SKILL_MATCHING.md`.

## Key files and commands

- _localsetup/lib/data_paths.sh, lib/json_formatter.sh
- _localsetup/tools/verify_context, verify_rules
- _localsetup/tests/automated_test.sh
- From repo root: `./_localsetup/tools/verify_context`, `./_localsetup/tests/automated_test.sh`

# Localsetup v2  - Context and skills index

| Asset | Description | When applied |
|-------|-------------|--------------|
| localsetup-context.mdc | Master rule: overview, invariants, skills index, docs index | Always |
| localsetup-decision-tree-workflow | Decision tree / reverse prompt; one Q per turn, 4 options A-D | User says "decision tree" or "reverse prompt"; editing .agent/queue/**, PRD |
| localsetup-agentic-umbrella-queue | Umbrella/queue; named workflows; impact summary + confirmation | Queue/PRD in scope |
| localsetup-agentic-prd-batch | Process PRDs; implement per spec; status; outcome | "Process PRDs", "run batch from PRD folder" |
| localsetup-public-repo-identity | Public repo identity; use local-identity for PII | Editing README*, CONTRIBUTING* |
| localsetup-framework-compliance | Pre-task workflow, checkpoints, document maintenance | Framework mods, PRDs, checklist tasks |
| localsetup-safety-and-backup | Security, backup, temp files, firewall | Destructive ops, system config, backups |
| localsetup-script-and-docs-quality | Markdown/encoding, script quality, file/docs discipline | Generating scripts, editing markdown/docs |
| localsetup-communication-and-tools | Communication, tool selection, periodic updates | Communication style, tools, MCP |
| localsetup-tmux-shared-session-workflow | Shared tmux session; sudo discovery and single-prompt gate (join session, trigger, batch until timeout); agent captures output; human can attach/sudo | Server commands, deployments, tmux, human-in-the-loop ops |
| localsetup-automatic-versioning | Automatic semantic versioning from conventional commits; VERSION, sync to READMEs/docs | Version bumps, release workflow, conventional commits, versioning docs |
| localsetup-github-publishing-workflow | Publishing checklist, doc structure, licensing, scrub for PII/secrets | Publishing to GitHub, public release prep, publishing checklist, repo readiness |
| localsetup-skill-creator | Create framework skill from workflow description or existing doc/markdown/GitHub | Create new skill, capture workflow as skill, adapt doc or skill into framework |
| localsetup-skill-importer | Import skills from URL (e.g. GitHub) or local path; discover, validate, screen, summarize; user picks which to import | Import skills from URL/path, screen external skills, add skills from repo |
| localsetup-skill-discovery | Discover public skills from registries; recommend top 5 similar when creating/importing; in-depth summary, use public, continue, or adapt | Creating/importing skill; find similar public skills; PUBLIC_SKILL_REGISTRY.urls, PUBLIC_SKILL_INDEX.yaml |
| localsetup-task-skill-matcher | Match task intent to installed skills; top-3 ranking, confirm/auto-pick flow, batch parcel options, and complementary public-skill suggestions | User asks "what skill should I use?", "pick the best", or task-to-skill match is unclear |
| localsetup-backlog-and-reminders | Record deferred ideas, to-dos, reminders (optional due or "whenever"); show due/overdue on session start or when asked | "Add to backlog", "remind me", "what's due?", "show my backlog", "start my session" |
| localsetup-humanizer | Humanize text; remove AI-writing patterns and add natural voice (rules-based, Wikipedia Signs of AI writing) | Editing or reviewing text to sound more natural and human-written |
| localsetup-test-runner | Write and run tests across languages and frameworks (Vitest, Jest, pytest, Playwright) | Generating or running tests, TDD, coverage |
| localsetup-tdd-guide | TDD workflow, test generation, coverage analysis, red-green-refactor | Generate tests, analyze coverage, TDD cycles |
| localsetup-receiving-code-review | Use when receiving code review feedback; verify before implementing | After code review; implementing or responding to feedback |
| localsetup-pr-reviewer | Automated GitHub PR code review with diff analysis, lint | Reviewing pull requests before merge |
| localsetup-debug-pro | Systematic debugging methodology and language-specific debugging commands | Debugging failures, reproducing bugs, regression tests |
| localsetup-git-workflows | Advanced git (rebase, bisect, worktree, reflog, conflicts) | Rebase, bisect, worktrees, recovery |
| localsetup-unfuck-my-git-state | Diagnose and recover broken Git state and worktree | Broken Git state, worktree errors, recovery |
| localsetup-skill-vetter | Security-first skill vetting before installing external skills | Before installing any skill from external source |
| localsetup-mcp-builder | Guide for creating high-quality MCP servers (Python, TypeScript) | Building MCP servers, integrating external APIs |
| localsetup-arbiter | Push decisions to Arbiter Zebu for async human review | Plan review, architectural decisions, human approval |
| localsetup-ansible-skill | Ansible infra automation; server provisioning, config management, deployment | Ansible playbooks, multi-host orchestration, server config |
| localsetup-linux-service-triage | Diagnose Linux service issues (logs, systemd, PM2, Nginx, DNS) | Failing or misconfigured server apps, service triage |
| localsetup-linux-patcher | Automated Linux patching and Docker container updates | Server maintenance, security updates, multi-host patching |
| localsetup-skill-normalizer | Phase 1: documents (platform choice when platform-specific); Phase 2: tooling to framework standard | Normalize one or all skills; batch review imported or dropped-in skills |
| localsetup-skill-sandbox-tester | Test skills in isolated sandbox; smoke check; on failure use debug-pro; no repo writes until user approves | Validate skill after import, test skill in sandbox, ensure skill runs before production |
| localsetup-agentlens | Codebase navigation with agentlens hierarchy (INDEX.md, modules, outline, memory) | Explore codebases, find modules/symbols, TODOs/warnings; large repos |
| localsetup-framework-audit | Run doc, link, skill matrix, version/facts checks; optional --deep (Deep Analysis); output to user path only | User says "run audit", "run framework audit", or before release |
| localsetup-system-info | Quick system diagnostics: CPU, memory, disk, uptime | Capture server baseline, host layout and specs for further operations |
| localsetup-cron-orchestrator | Manage cron from manifest: triggers, sequenced tasks, on-boot delay | Create/remove/reorder cron tasks; install crontab fragment |
| localsetup-cloudflare-dns | Manage Cloudflare DNS records (list, create, modify, delete) and run zone surveys via flarectl | Adding, changing, or removing DNS records; zone survey; automated DNS snapshots |
| localsetup-npm-management | Manage Nginx Proxy Manager proxy hosts via REST API; coordinate Docker service deployments with NPM routing | Create/modify/remove NPM proxy hosts; diagnose 502s; backup/restore; Docker + NPM deploy workflows |

Framework docs: _localsetup/docs/ (AGENTIC_DESIGN_INDEX.md, WORKFLOW_REGISTRY.md, PRD_SCHEMA_EXTERNAL_AGENT_GUIDE.md).

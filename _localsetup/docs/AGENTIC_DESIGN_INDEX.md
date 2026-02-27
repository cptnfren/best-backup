---
status: ACTIVE
version: 2.8
---

# Agentic design index (Localsetup v2)

**Purpose:** Index of agentic-design documentation. Paths are relative to _localsetup/docs/ (repo-local). Audience: humans and AI agents.

Copyright (c) 2026 Crux Experts LLC. MIT License  - see repository root [LICENSE](../../LICENSE).

## Core docs

| Doc | Description |
|-----|-------------|
| [WORKFLOW_REGISTRY.md](WORKFLOW_REGISTRY.md) | Named workflows; when to use; impact review |
| [PRD_SCHEMA_EXTERNAL_AGENT_GUIDE.md](PRD_SCHEMA_EXTERNAL_AGENT_GUIDE.md) | PRD/spec format, outcome template, external confirmation |
| [DECISION_TREE_WORKFLOW.md](DECISION_TREE_WORKFLOW.md) | Decision tree: one Q per turn, 4 options A-D, preferred + rationale |
| [AGENTIC_UMBRELLA_WORKFLOWS.md](AGENTIC_UMBRELLA_WORKFLOWS.md) | Umbrella workflows: single kickoff, PHC gates, single final webhook |
| [AGENTIC_AGENT_Q_PATTERN.md](AGENTIC_AGENT_Q_PATTERN.md) | Agent Q (queue) pattern: locate, implement, status, outcome |
| [DOCUMENT_LIFECYCLE_MANAGEMENT.md](DOCUMENT_LIFECYCLE_MANAGEMENT.md) | Doc status (ACTIVE/PROPOSAL/DRAFT); check before assuming implemented |
| [OUTPUT_AND_DOC_GENERATION.md](OUTPUT_AND_DOC_GENERATION.md) | Platform default: rich output (code blocks, lists, typography, links, glyphs, humanized prose) for all generated content |
| [REPO_AND_DATA_SEPARATION.md](REPO_AND_DATA_SEPARATION.md) | Engine at _localsetup/; local context vs framework; propose via PRD |
| [GIT_TRACEABILITY.md](GIT_TRACEABILITY.md) | Attach git hash when referencing PRDs, specs, outcomes |
| [SKILLS_AND_RULES.md](SKILLS_AND_RULES.md) | How master rule and skills interact; when to load which skill |
| [MULTI_PLATFORM_INSTALL.md](MULTI_PLATFORM_INSTALL.md) | Install for supported platforms |
| [PLATFORM_REGISTRY.md](PLATFORM_REGISTRY.md) | **Canonical list of supported AI agent platforms**; context/skills paths; skill registration file list |
| [AGENT_SKILLS_COMPLIANCE.md](AGENT_SKILLS_COMPLIANCE.md) | Agent Skills spec compliance; skill document versioning (metadata.version); auto-bump on commit |
| [SKILL_INTEROPERABILITY.md](SKILL_INTEROPERABILITY.md) | Import external skills (e.g. Anthropic); export our skills; full interchange with spec-compliant hosts |
| [SKILL_IMPORTING.md](SKILL_IMPORTING.md) | Import from URL or path; discover, validate, security-screen, summarize; user selects which skills to import; normalization (Phase 1 + Phase 2) mandatory |
| [SKILL_NORMALIZATION.md](SKILL_NORMALIZATION.md) | Phase 1: document normalization (platform choice when platform-specific). Phase 2: tooling rewrite to framework standard. Spec compliance and approval flow. |
| [SKILL_DISCOVERY.md](SKILL_DISCOVERY.md) | Public skill registries ([PUBLIC_SKILL_REGISTRY.urls](PUBLIC_SKILL_REGISTRY.urls), [PUBLIC_SKILL_INDEX.yaml](PUBLIC_SKILL_INDEX.yaml)); recommend similar when creating/importing |
| [TASK_SKILL_MATCHING.md](TASK_SKILL_MATCHING.md) | Task-to-installed-skill matching flow: single vs batch, auto-pick/parcel, complementary public-skill suggestions |
| [ops/tmux-ops-remote.md](ops/tmux-ops-remote.md) | Tmux ops when tmux runs on another host: REMOTE_TMUX_HOST, REMOTE_TMUX_CWD; use tmux_ops send as usual |
| [TMUX_TERMINAL_MODE.md](TMUX_TERMINAL_MODE.md) | Tmux-default terminal mode: enable/disable/status, ide vs shell mode, flags, manual rollback, layer reference |

## Skills index (in repo)

- **Per platform:** See [PLATFORM_REGISTRY.md](PLATFORM_REGISTRY.md) for context loader and skills paths. Cursor: `.cursor/rules/localsetup-context-index.md` lists master rule and all skills; same skills apply across platforms.

## Quick reference

- **Run decision tree:** Load skill localsetup-decision-tree-workflow; see [DECISION_TREE_WORKFLOW.md](DECISION_TREE_WORKFLOW.md).
- **Process queue / PRDs:** Load localsetup-agentic-prd-batch; see [PRD_SCHEMA_EXTERNAL_AGENT_GUIDE.md](PRD_SCHEMA_EXTERNAL_AGENT_GUIDE.md), [WORKFLOW_REGISTRY.md](WORKFLOW_REGISTRY.md).
- **Umbrella workflow:** Load localsetup-agentic-umbrella-queue; see [WORKFLOW_REGISTRY.md](WORKFLOW_REGISTRY.md).
- **Create a new skill:** Load localsetup-skill-creator; see [SKILL_INTEROPERABILITY.md](SKILL_INTEROPERABILITY.md).
- **Import skills from URL or path:** Load localsetup-skill-importer; run `_localsetup/tools/skill_importer_scan <path>`; see [SKILL_IMPORTING.md](SKILL_IMPORTING.md).
- **Discover similar public skills:** Load localsetup-skill-discovery when creating or importing; uses [PUBLIC_SKILL_REGISTRY.urls](PUBLIC_SKILL_REGISTRY.urls) and [PUBLIC_SKILL_INDEX.yaml](PUBLIC_SKILL_INDEX.yaml); see [SKILL_DISCOVERY.md](SKILL_DISCOVERY.md).
- **Audit and scrub the public skill index:** Run `python3 _localsetup/tools/skill_index_scrub.py` to check for dead URLs, stub/placeholder descriptions, and schema gaps. Add `--fix` to fetch real descriptions from upstream and write them back. Add `--report FILE` for a GFM report.
- **Tmux shared session and sudo:** Load localsetup-tmux-shared-session-workflow; use tool `_localsetup/tools/tmux_ops` (pick, probe, send, wait). Skill defines sudo gate via probe (ready vs password_required); use `send --wait` for short commands or `wait --timeout N` for long ops; never use raw tmux send-keys. For remote/VMs: see [ops/tmux-ops-remote.md](ops/tmux-ops-remote.md) (REMOTE_TMUX_HOST). See WORKFLOW_REGISTRY.md.
- **Tmux-default terminal mode:** Run `_localsetup/tools/tmux_terminal_mode enable [--mode ide|shell]` to wire up automatic tmux session launch (IDE terminal profile or shell RC auto-attach) and inject the mandatory agent ops rule. `disable` restores originals from backup. `status` reports all layers. See [TMUX_TERMINAL_MODE.md](TMUX_TERMINAL_MODE.md).
- **Run framework audit:** Load localsetup-framework-audit; run from repo root with `--output /path/to/report.md` (or set `LOCALSETUP_AUDIT_OUTPUT`). Optional `--deep` runs Deep Analysis (derive invocations from SKILL.md and script `--help`, run in sandbox, summary JSON + sidecar tarball; requires output path). See [WORKFLOW_REGISTRY.md](WORKFLOW_REGISTRY.md).

---

<p align="center">
<strong>Author:</strong> <a href="https://github.com/cptnfren">Slavic Kozyuk</a><br>
<strong>Copyright</strong> © 2026 <a href="https://www.cruxexperts.com/">Crux Experts LLC</a> – Innovate, Automate, Dominate.
</p>

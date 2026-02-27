---
status: ACTIVE
version: 2.8
---

# Skills and rules (Localsetup v2)

**Purpose:** How the master rule (or platform context loader) and skills interact; when to load which skill; cross-platform paths.

## Model

- **One always-loaded context** per platform: Cursor uses `.cursor/rules/localsetup-context.mdc`; Claude Code uses `.claude/CLAUDE.md`; Codex uses `AGENTS.md`; OpenClaw uses a context skill + optional doc template in _localsetup/docs/.
- **Skills:** Same SKILL.md content across platforms; installer/deploy copies from `_localsetup/skills/` to platform path (`.cursor/skills/`, `.claude/skills/`, `.agents/skills/`, or `skills/` for OpenClaw). Edit only in _localsetup; deploy overwrites platform paths.
- **When to load a skill:** Load when the task matches the skill's description (e.g. user says "decision tree" -> localsetup-decision-tree-workflow). The master rule/context includes an index of skills and when to use them.

## Task-to-skill matching flow

- **Mode detection:** Treat as **batch** when user request includes multiple distinct subtasks, or says "batch", "multiple steps", or "run the whole thing". Otherwise treat as **single task**.
- **Named skill override:** If user names a specific skill, load that skill directly. Do not run task-skill-matcher.
- **When to invoke matcher:** When uncertain which skill fits, or when user asks "what skill should I use?" / "pick the best", load `localsetup-task-skill-matcher`.
- **Single task behavior:** If one clear installed match exists, ask once "Use this skill?" before loading. In the same response, include up to 3 complementary public skills from [PUBLIC_SKILL_INDEX.yaml](PUBLIC_SKILL_INDEX.yaml) (one-line reason each). If index is missing or stale (`updated` older than 7 days), ask whether to refresh before complementary suggestions.
- **Batch behavior:** Prompt once at start with options: auto-pick for whole job, parcel-by-parcel prompts, or parcel auto-pick. If auto-pick is chosen, state planned skill sequence first, then proceed without repeated skill prompts.
- **No installed fit:** Say that no installed skill fits, offer up to 3 complementary public skills to import, and optionally suggest creating a skill via `localsetup-skill-creator`.
- **Reference:** Full procedure and output format live in skill `localsetup-task-skill-matcher` and [TASK_SKILL_MATCHING.md](TASK_SKILL_MATCHING.md).

## Platform paths

**Canonical list:** Supported platforms and their context/skills paths are defined in [PLATFORM_REGISTRY.md](PLATFORM_REGISTRY.md). Reference that file when listing platforms or adding a new one. Summary:

| Platform | Context loader | Skills |
|----------|----------------|--------|
| Cursor | .cursor/rules/localsetup-context.mdc | .cursor/skills/localsetup-*/ |
| Claude Code | .claude/CLAUDE.md | .claude/skills/localsetup-*/ |
| Codex | AGENTS.md (repo root) | .agents/skills/localsetup-*/ |
| OpenClaw | Skill localsetup-context + _localsetup/templates/openclaw/OPENCLAW_CONTEXT.md | skills/localsetup-*/ |

## Format

- Skills follow the [Agent Skills](https://agentskills.io/specification) specification: SKILL.md with required `name` and `description` frontmatter; optional `metadata.version` for skill document versioning; body = instructions. Same files work on all platforms.
- **Skill document versioning:** Each skill includes `metadata.version` (e.g. `"1.0"`). Skill version bumps are performed by the repository maintainers when skill files change; see [AGENT_SKILLS_COMPLIANCE.md](AGENT_SKILLS_COMPLIANCE.md).
- When adding a platform or registering a new skill, use [PLATFORM_REGISTRY.md](PLATFORM_REGISTRY.md) as the source of truth.
- **Interoperability:** Skills are [Agent Skills](https://agentskills.io/specification)–compliant and interchangeable: our skills work in any spec-compliant host; external skills (e.g. [Anthropic’s](https://github.com/anthropics/skills)) can be used here with placement + registration. See [SKILL_INTEROPERABILITY.md](SKILL_INTEROPERABILITY.md).

---

<p align="center">
<strong>Author:</strong> <a href="https://github.com/cptnfren">Slavic Kozyuk</a><br>
<strong>Copyright</strong> © 2026 <a href="https://www.cruxexperts.com/">Crux Experts LLC</a> – Innovate, Automate, Dominate.
</p>

---
status: ACTIVE
version: 2.8
---

# Task-to-skill matching (Localsetup v2)

**Purpose:** Define how agents map user tasks to installed skills with minimal interruption, plus complementary recommendations from the public skill index.

## Scope

- Applies to normal task execution when user does not name a specific skill.
- Complements (does not replace) [SKILLS_AND_RULES.md](SKILLS_AND_RULES.md).
- Detailed execution procedure lives in skill `localsetup-task-skill-matcher`.

## Core behavior

1. **Mode detection**
   - Treat as **batch** when user request includes multiple distinct subtasks, or says "batch", "multiple steps", or "run the whole thing".
   - Otherwise treat as **single task**.

2. **Named-skill override**
   - If user names a specific skill, load that skill directly.
   - Do not run task-skill-matcher in that case.

3. **When to invoke matcher**
   - Invoke `localsetup-task-skill-matcher` when skill choice is uncertain, or when user asks "what skill should I use?" / "pick the best".

4. **Single-task flow**
   - If one clear installed match exists, ask once: "Use this skill?"
   - In the same response, include up to 3 complementary public skills (one-line reason each).

5. **Batch flow**
   - Prompt once at start with options: auto-pick for full run, parcel prompts, or parcel auto-pick.
   - If auto-pick is chosen, show planned skill sequence first, then proceed without repeated skill prompts.
   - If parcel phases are unclear, propose one parcel (whole task).

6. **No installed fit**
   - Say no installed skill fits.
   - Offer up to 3 complementary public skills to import.
   - Optionally suggest creating a new skill via `localsetup-skill-creator`.

## Public index handling

- Source: [PUBLIC_SKILL_INDEX.yaml](PUBLIC_SKILL_INDEX.yaml)
- Stale definition: file missing, missing `updated`, or `updated` older than 7 days.
- If index is missing/stale while providing complementary suggestions:
  - Still present installed-skill match and "Use this skill?" first.
  - Then ask whether to refresh the public index.

## Platform paths

Use the current platform context loader/index per [PLATFORM_REGISTRY.md](PLATFORM_REGISTRY.md):

- Cursor: `.cursor/rules/localsetup-context-index.md` (or skills section in `.cursor/rules/localsetup-context.mdc`)
- Claude Code: `.claude/CLAUDE.md`
- Codex: `AGENTS.md`
- OpenClaw: context path per platform registry

## References

- [SKILLS_AND_RULES.md](SKILLS_AND_RULES.md)
- [PLATFORM_REGISTRY.md](PLATFORM_REGISTRY.md)
- Skill: `localsetup-task-skill-matcher`

---

<p align="center">
<strong>Author:</strong> <a href="https://github.com/cptnfren">Slavic Kozyuk</a><br>
<strong>Copyright</strong> © 2026 <a href="https://www.cruxexperts.com/">Crux Experts LLC</a> – Innovate, Automate, Dominate.
</p>

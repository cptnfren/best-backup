---
status: ACTIVE
version: 2.8
---

# Skill interoperability (Localsetup v2)

**Purpose:** Framework skills are [Agent Skills](https://agentskills.io/specification)–compliant so they can be used in any spec-compliant host. External skills (e.g. from [Anthropic’s skills](https://github.com/anthropics/skills)) can be used in this framework with minimal adaptation. Skills are interchangeable across ecosystems that follow the same spec.

## Interoperability principle

- **Our skills** use only the Agent Skills spec: required `name` and `description`, optional `metadata.version`, optional `license` / `compatibility`. Directory layout is `SKILL.md` plus optional `scripts/`, `references/`, `assets/`. No framework-only required fields. They are valid Agent Skills and can be copied into another host (e.g. Claude Code, Anthropic’s skills repo) as-is; the `localsetup-*` name is a convention, not a spec requirement.
- **External skills** that comply with the Agent Skills spec can be used in this framework by copying them into `_localsetup/skills/`, optionally renaming to `localsetup-*` for consistency, adding `metadata.version` if missing, and registering them in our platform indexes (see below). No change to the skill body or structure is required for spec compliance.

## Using an external skill in this framework (import)

1. **Obtain the skill**  - Clone or download a spec-compliant skill (e.g. from [anthropics/skills](https://github.com/anthropics/skills)) so you have a directory containing `SKILL.md` and any optional `scripts/`, `references/`, `assets/`.
2. **Copy into the framework**  - Place it under `_localsetup/skills/<skill-name>/`. If you want it to follow our naming convention, use `_localsetup/skills/localsetup-<name>/` and set `name: localsetup-<name>` in the frontmatter (directory name must match `name` per spec).
3. **Add metadata.version if missing**  - Ensure frontmatter includes `metadata.version: "1.0"` (or any string) so our versioning hook can bump it. The spec allows optional `metadata`; we use it for document versioning.
4. **Register**  - Add the skill to every file listed in [PLATFORM_REGISTRY.md](PLATFORM_REGISTRY.md) § “Skill registration (new skills)” so it appears in each platform’s context index. Use a short “When to use” line consistent with the skill’s `description`.
5. **Deploy**  - Run deploy (or rely on existing deploy) so platform-specific paths get the new skill. The skill content is already spec-compliant; no body changes are required for interoperability.

## Using a framework skill elsewhere (export)

- **Copy the skill directory**  - Use `_localsetup/skills/<name>/`. After deploy, the skill is also at the platform's skills path (e.g. `.cursor/skills/<name>/` for Cursor).
- **Use in any Agent Skills host**  - The directory is a valid Agent Skills skill. The host only needs to support the [Agent Skills](https://agentskills.io/specification) format (SKILL.md with `name` and `description`, optional dirs). No need to change the skill; `localsetup-*` is a naming choice and does not affect spec validity.
- **Optional**  - If the target host expects a different name, rename the directory and the `name` field so they match (spec requirement). Paths inside the skill (e.g. `_localsetup/docs/...`) may be framework-specific; the host can ignore or map them as needed.

## Specification and design references

- **Format (required for interchange):** [Agent Skills specification](https://agentskills.io/specification)  - [agentskills/agentskills](https://github.com/agentskills/agentskills).
- **Design and authoring:** [Anthropic’s skill-creator](https://github.com/anthropics/skills/tree/main/skills/skill-creator)  - principles (concise, degrees of freedom), anatomy (scripts/references/assets), progressive disclosure, what to include/avoid. Our skill-creator adds framework placement and registration; for structure and content design, follow the Agent Skills spec and Anthropic’s guidance so skills remain portable.
- **Validation:** [skills-ref](https://github.com/agentskills/agentskills/tree/main/skills-ref)  - `skills-ref validate path/to/skill` to check frontmatter and naming.

## Summary

| Direction | Action |
|-----------|--------|
| **External → Framework** | Copy skill dir into `_localsetup/skills/`; optionally rename to `localsetup-*`; add `metadata.version` if missing; register per PLATFORM_REGISTRY. |
| **Framework → External** | Copy `_localsetup/skills/<name>/` (or `.cursor/skills/<name>/`); use as-is in any Agent Skills host; optionally rename dir and `name` to match host conventions. |

Skills that follow the Agent Skills spec are interchangeable; this framework adds placement, registration, and optional `metadata.version` for versioning, without breaking spec compliance.

---

<p align="center">
<strong>Author:</strong> <a href="https://github.com/cptnfren">Slavic Kozyuk</a><br>
<strong>Copyright</strong> © 2026 <a href="https://www.cruxexperts.com/">Crux Experts LLC</a> – Innovate, Automate, Dominate.
</p>

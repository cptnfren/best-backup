---
status: ACTIVE
version: 2.8
---

# Repo and data separation (Localsetup v2)

**Purpose:** The framework lives in the client repo at `_localsetup/`. Only modify local context (e.g. `.cursor/rules/local-*.mdc`) or propose changes via PRD; do not edit framework engine files in place for one-off overrides.

## Separation

- **Engine**  - Contents of `_localsetup/` (framework code, docs, skills, templates). Upgrades replace this folder; do not rely on local edits inside it for permanent overrides.
- **Local context**  - Repo-root files such as `.cursor/rules/local-*.mdc` or platform-specific overrides. Safe to edit for project-specific rules.
- **Proposals**  - For framework behavior changes, use the Agent Q / PRD flow; see [PRD_SCHEMA_EXTERNAL_AGENT_GUIDE.md](PRD_SCHEMA_EXTERNAL_AGENT_GUIDE.md).

## Reference

- [GIT_TRACEABILITY.md](GIT_TRACEABILITY.md)  - Attach git hash when referencing PRDs, specs, outcomes.
- [AGENTIC_DESIGN_INDEX.md](AGENTIC_DESIGN_INDEX.md)  - Index of framework docs.

---

<p align="center">
<strong>Author:</strong> <a href="https://github.com/cptnfren">Slavic Kozyuk</a><br>
<strong>Copyright</strong> © 2026 <a href="https://www.cruxexperts.com/">Crux Experts LLC</a> – Innovate, Automate, Dominate.
</p>

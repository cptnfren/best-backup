---
status: ACTIVE
version: 2.8
---

# Agent Q (queue) pattern (Localsetup v2)

**Purpose:** Pattern for processing a queue of PRD/spec items: locate specs, implement per spec, update status, write outcome. Used when the user says "process PRDs" or "run batch from PRD folder".

## Queue flow

1. **Locate**  - Find PRD/spec files in the configured path (e.g. `.agent/queue/`). Filter by status (e.g. `ready`, `in-progress`). Sort by priority and date.
2. **Implement**  - For each spec, follow Implementation steps and Acceptance criteria; use [PRD_SCHEMA_EXTERNAL_AGENT_GUIDE.md](PRD_SCHEMA_EXTERNAL_AGENT_GUIDE.md) for format and outcome template.
3. **Status**  - Set `status: in-progress` when starting; `status: done` or `blocked` when finished.
4. **Outcome**  - Append outcome block (branch, commit SHA, files changed, verification, rollback) per spec.
5. **Clean-tree**  - Before marking done, ensure repo is clean (commit or revert as needed).
6. **External confirmation**  - If spec has `external_confirmation: acknowledged` or equivalent, agent may skip human impact confirmation; otherwise follow guardrails.

## Reference

- [PRD_SCHEMA_EXTERNAL_AGENT_GUIDE.md](PRD_SCHEMA_EXTERNAL_AGENT_GUIDE.md)  - Spec format, front matter, outcome template.
- [WORKFLOW_REGISTRY.md](WORKFLOW_REGISTRY.md)  - When to use Agent Q and impact review.

---

<p align="center">
<strong>Author:</strong> <a href="https://github.com/cptnfren">Slavic Kozyuk</a><br>
<strong>Copyright</strong> © 2026 <a href="https://www.cruxexperts.com/">Crux Experts LLC</a> – Innovate, Automate, Dominate.
</p>

---
status: ACTIVE
version: 2.8
---

# PRD schema and external agent guide (Localsetup v2)

**Purpose:** PRD/spec format, front matter, lifecycle, outcome template. When referencing repo artifacts, attach git hash (see GIT_TRACEABILITY.md).

## Spec format

- **Front matter:** status (ready | in-progress | done | blocked), priority, optional external_confirmation, impact_review.
- **Sections:** Implementation steps, Acceptance criteria, Verification plan, Rollback plan.
- **Outcome block:** Append per spec (commit SHA, files changed, verification, rollback command).

## Queue and batch

- Specs in `.agent/queue/` (or configured path). Exclude README, INDEX, SPEC-TEMPLATE.
- Filter by status; sort by priority then filename. Implement per spec; update status; write outcome.
- **Clean-tree:** Before marking done, repo clean (commit or revert). See skill localsetup-agentic-prd-batch.

## External confirmation

- If spec has external_confirmation acknowledged or impact_review confirmed by external agent, implementer may skip human impact confirmation; otherwise follow guardrails (impact summary + user confirmation for big/destructive).

## Related

- GIT_TRACEABILITY.md
- WORKFLOW_REGISTRY.md

---

<p align="center">
<strong>Author:</strong> <a href="https://github.com/cptnfren">Slavic Kozyuk</a><br>
<strong>Copyright</strong> © 2026 <a href="https://www.cruxexperts.com/">Crux Experts LLC</a> – Innovate, Automate, Dominate.
</p>

---
status: ACTIVE
version: 2.8
---

# Agentic umbrella workflows (Localsetup v2)

**Purpose:** Definition of umbrella workflows: single kickoff, no mid-run stop, PHC (pre-human-confirmation) gates, single final webhook. For the list of named workflows and when to use them, see [WORKFLOW_REGISTRY.md](WORKFLOW_REGISTRY.md).

## Umbrella invariants

- **Single kickoff**  - User invokes one named workflow; execution runs through defined phases without requiring repeated "continue" for each step.
- **No mid-run stop**  - Once started (after impact confirmation if required), the workflow runs to completion or a defined gate; the agent does not pause for approval between every sub-step unless the workflow spec defines such a gate.
- **PHC gates**  - Pre-human-confirmation gates may be defined for destructive or high-impact steps; at those gates the agent presents impact and waits for explicit user confirmation before proceeding.
- **Single final webhook**  - One outcome/notification at the end (e.g. status, summary, or external webhook) rather than many intermediate pings.

## Reference

- [WORKFLOW_REGISTRY.md](WORKFLOW_REGISTRY.md)  - Named workflows, when to use, impact review.
- [PRD_SCHEMA_EXTERNAL_AGENT_GUIDE.md](PRD_SCHEMA_EXTERNAL_AGENT_GUIDE.md)  - Spec format and outcome template.

---

<p align="center">
<strong>Author:</strong> <a href="https://github.com/cptnfren">Slavic Kozyuk</a><br>
<strong>Copyright</strong> © 2026 <a href="https://www.cruxexperts.com/">Crux Experts LLC</a> – Innovate, Automate, Dominate.
</p>

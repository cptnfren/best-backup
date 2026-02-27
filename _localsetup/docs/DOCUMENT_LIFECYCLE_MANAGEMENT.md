---
status: ACTIVE
version: 2.8
---

# Document lifecycle (Localsetup v2)

**Purpose:** Framework docs in `_localsetup/docs/` must have a defined status. Check status before assuming a feature is implemented.

## Status values

| Status    | Meaning |
|-----------|---------|
| ACTIVE    | In effect; use as current guidance. |
| PROPOSAL  | Under consideration; not yet implemented. Do not assume behavior is in place. |
| DRAFT     | Work in progress; may change. |
| DEPRECATED| No longer recommended; see replacement if noted. |
| ARCHIVED  | Retained for reference only. |

## Practice

- Every framework doc under `_localsetup/docs/` (and in source `_localsetup/docs/`) should include YAML front matter with `status:` and, where applicable, `version:`.
- Before referencing a doc for core rules or behavior, check its status. If PROPOSAL, confirm with the user before relying on described behavior.
- See [AGENTIC_DESIGN_INDEX.md](AGENTIC_DESIGN_INDEX.md) for the index of framework docs.

---

<p align="center">
<strong>Author:</strong> <a href="https://github.com/cptnfren">Slavic Kozyuk</a><br>
<strong>Copyright</strong> © 2026 <a href="https://www.cruxexperts.com/">Crux Experts LLC</a> – Innovate, Automate, Dominate.
</p>

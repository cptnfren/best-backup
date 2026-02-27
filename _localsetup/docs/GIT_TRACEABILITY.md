---
status: ACTIVE
version: 2.8
---

# Git traceability (Localsetup v2)

**Purpose:** When referencing a repo artifact (file, PRD, document) in PRDs, specs, outcomes, or handoffs, **attach the git hash** so the reference is immutable and point-in-time.

## Principle

- Repos evolve; "PRD.md" without a version is ambiguous. **Rule:** When referencing a particular file, product, or document in PRDs, specs, outcomes, or bi-directional communications, attach the git hash (commit SHA or blob ref) for that artifact at the time of the reference.

## Why

- **Traceability:** Know exactly which version was the basis for a decision or implementation.
- **Audit and rollback:** Immutable references support audit and safe rollback.
- **Handoffs:** External agents and implementers agree on which version they are discussing.

## How

- **By commit:** `path/to/file.md` at commit `<sha>` (e.g. `PRD.md @ a1b2c3d`).
- **In front matter:** e.g. `ref_commit: a1b2c3d` or `referenced_artifacts: [{ path: "PRD.md", sha: "a1b2c3d" }]`.
- **In outcomes:** When outcome references another document (e.g. "per spec X"), include that spec's path and commit at which it was read.

## Scope

- Applies to all PRDs, queue specs, outcomes, and messages that reference repo files. Does not replace normal use of paths for "current" context; hash is required when the reference must be stable across time.

---

<p align="center">
<strong>Author:</strong> <a href="https://github.com/cptnfren">Slavic Kozyuk</a><br>
<strong>Copyright</strong> © 2026 <a href="https://www.cruxexperts.com/">Crux Experts LLC</a> – Innovate, Automate, Dominate.
</p>

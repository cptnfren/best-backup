---
status: ACTIVE
version: 2.8
---

# Skill importing (Localsetup v2)

**Purpose:** How to import external skills from a URL (e.g. GitHub) or local path: discover skills, validate and screen for safety, summarize for the user, and let them choose which to import. Compatible with [Agent Skills](https://agentskills.io/specification) and sources like [Anthropic's skills](https://github.com/anthropics/skills).

## Sources

- **URL**  - GitHub repo (e.g. `https://github.com/anthropics/skills`), raw archive URL, or any HTTP(S) URL the agent can fetch. The agent clones or downloads to a temporary directory, then runs the scan tool on that path.
- **Local path**  - Directory on disk (e.g. `./downloaded-skills/skills/`) containing one or more skill directories.
- **Local markdown**  - A single SKILL.md or a doc the user wants turned into a skill; use the [skill-creator](SKILL_INTEROPERABILITY.md) workflow to create a new skill from it.

## Adding a skill from paste or URL

When the source is **pasted content** (e.g. user pastes SKILL.md into chat) or a **URL to a single document** (not a repo), the agent must **never write directly to the final skill location**. Use this flow:

1. **Write to a temporary directory**  - Create a unique temp dir (e.g. `mktemp -d` or equivalent). Write the pasted or fetched content as `SKILL.md` (and any scripts/assets if present) into that dir.
2. **Run validation on that path**  - Run the scan/validation tool on the temp directory (e.g. `skill_validation_scan.py --scan-root <parent> --skill-dir <tempdir>`). Validation is always path-based; do not pass skill content through the shell or on stdin.
3. **Present results and user choices**  - Show content-safety results (references only: file, line, column, pattern, description from index). Offer: (1) Do not import / skip, (2) I have reviewed the file; proceed with import, (3) I will ignore and continue anyway.
4. **Copy only after approval**  - Only if the user approves, copy the temp dir (or its contents) into `_localsetup/skills/<name>/`. Do not modify the temp dir after validation.

If the agent cannot create a temp directory (permissions, no space), report that clearly and do not proceed with validation. Both **localsetup-skill-importer** and **localsetup-skill-creator** use this flow when the source is paste or a URL to a single document; see their SKILL.md for step-by-step use of this doc.

## Workflow (agent-driven)

1. **Obtain content**  - If URL: clone repo (e.g. `git clone --depth 1 <url> <tmpdir>`) or download archive and extract. If local path: use it as the scan root.
2. **Discover skills**  - Run the framework scan tool on the root path. It finds directories that contain `SKILL.md` with valid frontmatter (`name`, `description`).
3. **Validate and screen**  - For each candidate skill the tool:
   - Validates Agent Skills format (name matches directory, description present).
   - Lists what the skill has: files in `scripts/`, `references/`, `assets/`; types of code (e.g. Python, Bash).
   - Runs a heuristic security screen (no execution): flags patterns in scripts/assets (e.g. `eval`, `curl | sh`, encoded payloads). Results are advisory; the user decides.
   - Runs content-safety checks: pattern file against SKILL.md body and scripts/assets, plus strict English-only check on the body. For pattern hits, the tool outputs **references only** (file, line, column, pattern id, and a short description from the pattern index). The actual content at those positions is not read or displayed; the user opens the file and reviews. See [SKILL_VALIDATION_PATTERNS.md](SKILL_VALIDATION_PATTERNS.md).
4. **Summarize per skill**  - For each skill produce a brief:
   - **What it does**  - From `description` (and first paragraph of body if helpful).
   - **What it has**  - File count and types (scripts, references, assets); list script languages and notable files.
   - **Code / behavior**  - Kinds of code (Python, Bash, etc.) and any compatibility or dependency notes.
   - **Security screening**  - Pass / flags (e.g. "no concerns" or "Security: Review …" with file/line). Do not auto-block; present so the user can choose.
   - **Content safety**  - "No concerns" or "Content safety: REVIEW" with references (file, line, column, pattern, description from index). Do not read or display the flagged content; state that the user should open the file at the given position(s) and review, then offer: skip skill, proceed after review, or ignore and continue. Do not auto-block.
5. **User selects**  - Present the list and briefs; ask the user which skills to import (by name or "all"). Use AskQuestion or clear prompt so they can approve or skip.
6. **Duplicate, overlap, and namespace check**  - Before importing each selected skill, compare it to existing framework skills (list `_localsetup/skills/` and read each existing SKILL.md `name` and `description`). For each candidate:
   - **Namespace collision:** Same `name` or same directory name already exists in `_localsetup/skills/`. Warn the user and offer: **Ignore new** (skip this skill), **Replace existing** (overwrite with the new skill), **Merge** (combine best of both into one skill), or **Create as new** (import under a different name, e.g. `localsetup-<name>-v2`).
   - **Possible duplicate/overlap:** No name match but description or purpose is very similar to an existing skill (same domain, same triggers, overlapping "when to use"). Warn that overlap is likely and offer the same four options: **Ignore new**, **Replace existing**, **Merge**, or **Create as new** (user can confirm or pick a distinct name).
6b. **Normalize (mandatory)**  - For each selected skill, after security and content-safety have been verified (user has chosen to proceed), **always** run normalization. Use [SKILL_NORMALIZATION.md](SKILL_NORMALIZATION.md) as the single source of truth. **Phase 1:** When the skill is platform-specific, offer the user a choice (keep as is, keep platform-specific but normalized, or fully normalize); when not platform-specific, apply the full spec-compliance and platform-neutralization rules. Produce summary and key edits; get approval; copy the normalized skill. **Phase 2 (tooling):** Unless the user requests an exception (and accepts responsibility for supporting original tooling), rewrite all skill scripts to the framework's tooling standard; then update all documents so they describe the new tooling. Do not skip normalization; all imported skills must be normalized per the user's Phase 1 choice and Phase 2 (tooling by default).
7. **Import selected**  - For each selected skill, after user choice (and any merge/rename) and after the mandatory normalize step: copy the skill directory into `_localsetup/skills/<name>/` with the **normalized** SKILL.md; set `name` in frontmatter to match directory (e.g. `localsetup-<name>`); add `metadata.version: "1.0"` if missing; register per [PLATFORM_REGISTRY.md](PLATFORM_REGISTRY.md); run deploy if needed.

## Security and content safety screening (heuristic, no execution)

- **Scope**  - Static scan of file contents only. No execution of scripts or network calls by the tool.
- **Security (scripts/assets)**  - Patterns to flag (examples): `eval(`, `base64 -d` piped to shell, `curl | sh`, `Invoke-Expression`, `/etc/shadow`, NOPASSWD. Output: "Security: No heuristic concerns" or "Security: REVIEW (heuristic flags)" with file/line. Flag for user review rather than block.
- **Content safety**  - The tool uses a pattern file (see [SKILL_VALIDATION_PATTERNS.md](SKILL_VALIDATION_PATTERNS.md)) to scan SKILL.md body and optionally scripts/assets for prompt-injection, exfil, and similar patterns. It also checks that the skill body is 100% English (any non-allowed character triggers review). For pattern hits, output is **references only**: file, line, column, pattern id, and the pattern's description from the YAML. The tool does not read or display the actual content at those positions; the user opens the file and reviews. Offer: (1) Skip this skill, (2) I have reviewed; proceed, (3) Ignore and continue. Do not auto-block.
- **Pattern file**  - Location and 7-day refresh: [SKILL_VALIDATION_PATTERNS.md](SKILL_VALIDATION_PATTERNS.md). Canonical fetch URL documented there.

## Tool

- **Scan only (no fetch):** `_localsetup/tools/skill_importer_scan` (Bash) or `skill_importer_scan.ps1` (PowerShell). Run from repo root. Arguments: path to directory that may contain skill subdirs. Writes a per-skill summary (what it does, what it has, code types, security flags) to stdout (and optionally JSON to a file). The agent uses this after fetching a URL to a temp dir.
- **Fetch**  - The agent uses `git clone`, `curl`, or equivalent to obtain the URL content; then runs the scan tool on the resulting path.

## Duplicate, overlap, and namespace checks

- **Before importing,** the agent must check each candidate against existing framework skills so the user can avoid duplicates and naming conflicts.
- **How to check:** List existing skills from `_localsetup/skills/` (directory names and, for each, the `name` and `description` from SKILL.md frontmatter). Compare each selected candidate by (1) exact `name` or directory name, (2) similarity of description/purpose/triggers.
- **Namespace collision:** Candidate has the same `name` or same directory name as an existing skill. Always warn and offer: **Ignore new** (do not import), **Replace existing** (overwrite), **Merge** (combine best of both), **Create as new** (import with a different name).
- **High overlap:** No name match but the candidate is very similar in purpose/triggers to an existing skill. Warn that duplication/overlap is likely and offer the same four options. For **Merge**, the agent combines content from both (e.g. stronger description, merged sections, deduplicated steps) into one skill and replaces the existing one; then the incoming skill is not added as a second copy.
- **User choice is final.** Do not auto-replace or auto-merge without explicit user selection.

## Compatibility

- Imported skills must be [Agent Skills](https://agentskills.io/specification)–compliant (SKILL.md with `name`, `description`). The scan tool checks for this. After import, they work like any framework skill and are interchangeable (see [SKILL_INTEROPERABILITY.md](SKILL_INTEROPERABILITY.md)).

## Reference

- [SKILL_NORMALIZATION.md](SKILL_NORMALIZATION.md)  - Phase 1: document normalization (user choice when platform-specific: keep as is, keep platform-specific but normalized, or fully normalize). Phase 2: tooling normalization (rewrite to framework standard; exception available). Applied mandatorily during import after security is verified, or when using the standalone normalizer.
- [SKILL_VALIDATION_PATTERNS.md](SKILL_VALIDATION_PATTERNS.md)  - Pattern file location, fetch URL, 7-day refresh, content safety flow.
- [SKILL_INTEROPERABILITY.md](SKILL_INTEROPERABILITY.md)  - Import/export and spec alignment.
- [PLATFORM_REGISTRY.md](PLATFORM_REGISTRY.md)  - Where to register newly imported skills.
- Load skill **localsetup-skill-importer** when the user wants to import skills from a URL or local path, or when screening and selecting external skills.

---

<p align="center">
<strong>Author:</strong> <a href="https://github.com/cptnfren">Slavic Kozyuk</a><br>
<strong>Copyright</strong> © 2026 <a href="https://www.cruxexperts.com/">Crux Experts LLC</a> – Innovate, Automate, Dominate.
</p>

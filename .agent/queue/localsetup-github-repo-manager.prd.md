---
status: ready
priority: 1
type: skill
skill_id: localsetup-github-repo-manager
impact_review: required
external_confirmation: pending
ref_commit: 56deced5291ac6489b6843b4e15922298583f2cc
---

# PRD: localsetup-github-repo-manager

## Purpose

Create a new Agent Skills-compliant framework skill that packages a complete, generalized GitHub repository management and publishing automation system. The skill bundles Python tooling, a configuration schema, GitHub Actions workflows, and community health file templates. It is repo-agnostic: all identity fields, targets, and policies are driven by a `project.yaml` configuration file that the user populates for their specific project. No hardcoded project names, URLs, or author details appear in any part of the skill.

This skill is derived from and validated against a working implementation at commit `56deced` of the reference repo. It generalizes that implementation into a portable, installable framework skill.

---

## Background and motivation

Publishing a Python project to GitHub and keeping it well-maintained requires a repeatable set of tasks that most developers rebuild from scratch each time. The reference implementation solved this for one repo. This skill captures that solution as a framework primitive so any repo using Localsetup v2 can adopt it in minutes.

The skill covers:

- Project identity management (author, company, copyright) propagated to all files from a single YAML config
- Semantic version management driven by conventional commits
- CHANGELOG generation grouped by commit type
- Copyright footer stamping across all public markdown files
- GitHub community health files (CONTRIBUTING, CODE_OF_CONDUCT, issue templates, PR template)
- GitHub Actions CI/CD workflows (lint, syntax check, stale issues, auto GitHub Release on tag push)
- Doc staleness detection keyed to source file changes
- Broken internal link scanning across all public docs
- A single release command that runs all steps in order with dry-run and rollback support

---

## Skill specification

### Skill metadata (SKILL.md frontmatter)

```yaml
name: localsetup-github-repo-manager
description: >
  Complete GitHub repository management and publishing automation for Python projects.
  Manages project identity (author, company, copyright), semantic versioning from
  conventional commits, CHANGELOG generation, copyright footer stamping, GitHub community
  health files, and CI/CD workflows. Driven entirely by project.yaml with no hardcoded
  values. Use when setting up a new GitHub repo, cutting a release, updating project
  identity, or adding community health files and CI to an existing project.
metadata:
  version: "1.0"
compatibility: >
  Python >= 3.10. Requires PyYAML >= 6.0 (pip install pyyaml). Git CLI must be present.
  GitHub CLI (gh) optional but required for release creation workflow. ruff optional
  (used in CI lint workflow). All tooling is Python-only per framework TOOLING_POLICY.
```

---

## Deliverables

The agent implementing this PRD produces the following file tree inside the skill directory `_localsetup/skills/localsetup-github-repo-manager/`:

```
localsetup-github-repo-manager/
├── SKILL.md                          # Agent Skills-compliant skill definition
├── project.yaml.template             # Identity config template (copy to repo root as project.yaml)
├── scripts/
│   ├── stamp.py                      # Copyright footer stamper + code file identity syncer
│   ├── bump_version.py               # Semantic version bumper from conventional commits
│   ├── check_docs.py                 # Doc staleness + broken link checker
│   └── release.py                    # Full release workflow orchestrator
├── templates/
│   ├── github/
│   │   ├── CONTRIBUTING.md.tpl       # Contributor guide template
│   │   ├── CODE_OF_CONDUCT.md.tpl    # Contributor Covenant v2.1 template
│   │   ├── pull_request_template.md.tpl
│   │   ├── ISSUE_TEMPLATE/
│   │   │   ├── bug_report.md.tpl
│   │   │   └── feature_request.md.tpl
│   │   └── workflows/
│   │       ├── ci.yml.tpl            # Lint + syntax + import check, Python matrix
│   │       ├── stale.yml.tpl         # Stale issue/PR management
│   │       └── release-notes.yml.tpl # Auto GitHub Release on tag push
│   ├── CHANGELOG.md.tpl              # Keep a Changelog format seed
│   └── LICENSE.mit.tpl               # MIT License template
└── references/
    ├── project-yaml-schema.md        # Field-by-field reference for project.yaml
    ├── conventional-commits.md       # Commit prefix to bump type mapping
    └── release-workflow.md           # Full release step diagram and flags reference
```

---

## Implementation steps

### Step 1: Bootstrap skill directory

1. Create `_localsetup/skills/localsetup-github-repo-manager/` with the directory structure above.
2. Verify the skill directory name matches the `name` field in SKILL.md frontmatter exactly.
3. Do not create any files in the target repo yet; all repo-level changes are applied by the user running the skill's scripts.

### Step 2: Write SKILL.md

Produce a complete SKILL.md that satisfies the Agent Skills specification (as documented in `_localsetup/docs/AGENT_SKILLS_COMPLIANCE.md` and `_localsetup/docs/SKILL_NORMALIZATION.md`):

- Frontmatter: `name`, `description` (under 1024 chars), `metadata.version`, `compatibility`
- Body structured as: Purpose, Prerequisites, Quick start, Workflows (with subsections per tool), Configuration reference, Acceptance criteria
- Keep under 500 lines
- Platform-neutral: no references to specific repos, usernames, company names, or install-specific paths
- All script invocations shown as `python _localsetup/skills/localsetup-github-repo-manager/scripts/<script>.py`

#### SKILL.md body must cover these workflows

**Identity workflow:** User edits `project.yaml` at repo root, runs `stamp.py`, all docs and code files update in one command.

**Release workflow:** Single command `release.py` runs pre-flight, doc validation, identity stamp, version bump, CHANGELOG prepend, commit, tag, and push. Supports `--dry-run`, `--no-push`, `--allow-stale-docs`, `--major`/`--minor`/`--patch` force flags.

**Doc check workflow:** `check_docs.py` scans for broken internal links and flags docs that need review based on which source files changed since a given ref.

**Bootstrap workflow:** User runs install command from SKILL.md to copy `project.yaml.template` to repo root, copy `.github/` templates, optionally copy `CHANGELOG.md.tpl` and `LICENSE.mit.tpl` to repo root. Instructions walk the user through filling in `project.yaml` and running `stamp.py` for the first time.

### Step 3: Write `project.yaml.template`

Fully documented template. Every field has an inline comment explaining its purpose and which scripts use it. Fields:

```yaml
# project.yaml - project identity and stamp configuration
# Copy this file to your repo root as project.yaml and fill in your values.
# Run: python _localsetup/skills/localsetup-github-repo-manager/scripts/stamp.py

project:
  name: ""                # Short package/tool name (used in docs and setup.py)
  description: ""         # One-line description
  repository: ""          # Full GitHub URL: https://github.com/OWNER/REPO

author:
  name: ""                # Full name of the primary author
  github: ""              # GitHub username (no @)
  email: ""               # Optional. Leave blank to omit from setup.py

company:
  name: ""                # Company or organization name (linked in footer)
  url: ""                 # Company website URL

copyright:
  year: 2026              # Copyright year. Update annually or set to range "2024-2026"
  license: MIT            # License name shown in footer

# Markdown files that receive the centered copyright footer.
# Paths are relative to repo root. Edit to match your actual doc layout.
stamp_targets:
  - README.md
  - QUICKSTART.md
  - INSTALL.md
  - CHANGELOG.md
  - docs/README.md
  - .github/CONTRIBUTING.md
  - .github/CODE_OF_CONDUCT.md
```

### Step 4: Write Python scripts (in `scripts/`)

All four scripts must conform to the framework tooling standard as defined in `_localsetup/docs/TOOLING_POLICY.md` and `_localsetup/docs/INPUT_HARDENING_STANDARD.md`:

- Python 3.10+ only
- PyYAML for all YAML parsing (never parse YAML by hand)
- `require_deps()` from `lib.deps` at startup for dependency checking
- Hostile-by-default input handling: validate all CLI args, file paths, and config fields; emit actionable errors to stderr with context
- No silent failure on critical paths
- All file writes are atomic (write to temp, rename) or guarded by existence checks
- `--dry-run` flag on every script that modifies files or runs git commands
- All scripts are importable as modules (no bare module-level side effects)

#### `stamp.py` - Identity stamper

Behavior:
- Load `project.yaml` from repo root (path configurable via `--config`)
- Validate all required fields (author.name, company.name, company.url, copyright.year, project.repository); emit field-specific errors to stderr if missing
- Build footer HTML block: centered `<p>`, author name on line 1, `&copy; YEAR <a href="COMPANY_URL">COMPANY_NAME</a> &mdash; <a href="REPO/blob/main/LICENSE">LICENSE License</a>` on line 2
- Wrap footer in sentinel comments `<!-- project-footer:start -->` / `<!-- project-footer:end -->` for idempotent replacement
- For each path in `stamp_targets`: strip existing footer block if present, append two blank lines + footer block
- Sync identity to code files:
  - `setup.py`: `author=` field
  - `bbackup/__init__.py` (or equivalent): `__author__ =` field (path configurable; skip gracefully if not found)
  - `LICENSE`: copyright line matching pattern `Copyright (c) YEAR NAME`
- Output per-file status legend: `[+] stamped`, `[~] updated`, `[=] unchanged`, `[-] skipped`, `[!] no-match`
- Flags: `--dry-run`, `--no-docs`, `--no-code`, `--config PATH`

#### `bump_version.py` - Version bumper

Behavior:
- Read `VERSION` file from repo root
- Get commits since last git tag; if no tag exists, use root commit as base (not `HEAD`, to avoid scanning entire history)
- Classify commits by conventional commit prefix:
  - `BREAKING CHANGE:` in body or `type!:` prefix: major bump
  - `feat:` or `feat(scope):`: minor bump
  - All others: patch bump
- Write incremented version to `VERSION`
- Sync version string to configurable targets (default: `bbackup/__init__.py`, `setup.py`, `README.md`)
- Prepend new dated section to `CHANGELOG.md` using `generate_changelog_entry()`:
  - Group commits by section: Added (feat), Fixed (fix), Changed (perf/refactor), Documentation (docs), Maintenance (chore/test/ci/build)
  - Skip version bump commits from changelog entries
  - Update `[Unreleased]` comparison link and add new version link at bottom of CHANGELOG
- Flags: `--dry-run`, `--major`, `--minor`, `--patch` (force override)
- All functions importable: `read_version()`, `write_version()`, `get_commits_since_last_tag()`, `determine_bump_type()`, `parse_semver()`, `bump()`, `generate_changelog_entry()`, `prepend_changelog()`

#### `check_docs.py` - Doc staleness and link checker

Behavior:
- Accept `--since REF` (default `HEAD~1`; accepts `last-tag` as special value)
- Run `git diff --name-only SINCE HEAD` to get changed files
- Map changed source files to docs that should be reviewed using a configurable `SOURCE_TO_DOC_MAP` (list of source globs, doc paths, reason string)
- Scan all files in `PUBLIC_DOCS` list for broken internal markdown links: `[text](path)` where path is not `http`, not `#`, and the resolved target does not exist on disk
- Return structured `DocCheckResult` dataclass: `changed_sources`, `docs_to_review` (list of `(doc, reason)`), `broken_links` (list of `(doc, link)`)
- Exit code 0 if clean, 1 if issues found
- Flags: `--since REF`, `--verbose`, configurable `PUBLIC_DOCS` and `SOURCE_TO_DOC_MAP` via `--config`

#### `release.py` - Release orchestrator

Behavior (ordered steps, with step counter displayed):
1. Pre-flight: clean working tree (unless `--allow-dirty`), on release branch, remote reachable (unless `--no-push`)
2. Doc link check: call `check_docs.run()`; abort on broken links; flag stale docs unless `--allow-stale-docs`
3. Determine version bump: read commits, classify, determine bump type, compute new version; check tag does not already exist
4. Confirm: interactive `[y/N]` prompt showing current -> new version (skipped on `--dry-run`)
5. Stamp: call `stamp.stamp_docs()` and `stamp.sync_code_files()` to refresh all footers and identity fields
6. Bump and sync: call `bump_version.run()` to write new version and update all sync targets; prepend CHANGELOG entry
7. Commit: stage all modified files (VERSION, `__init__.py`, setup.py, README.md, CHANGELOG.md, LICENSE, all stamp targets); commit with message `chore: bump version to X.Y.Z`
8. Tag: create annotated git tag `vX.Y.Z` with message `Release vX.Y.Z`
9. Push (optional): push branch and tag to origin

Flags: `--dry-run`, `--no-push`, `--allow-dirty`, `--allow-stale-docs`, `--major`, `--minor`, `--patch`, `--since REF`, `--branch NAME` (default: main)

Step counter adjusts total automatically based on `--no-push`.

### Step 5: Write GitHub template files (in `templates/github/`)

All `.tpl` files use `{{PLACEHOLDER}}` substitution tokens that the bootstrap command replaces with values from `project.yaml`. Tokens:

| Token | Value |
|---|---|
| `{{PROJECT_NAME}}` | `project.name` |
| `{{REPO_URL}}` | `project.repository` |
| `{{AUTHOR_NAME}}` | `author.name` |
| `{{AUTHOR_GITHUB}}` | `author.github` |
| `{{COMPANY_NAME}}` | `company.name` |
| `{{COMPANY_URL}}` | `company.url` |
| `{{COPYRIGHT_YEAR}}` | `copyright.year` |
| `{{LICENSE}}` | `copyright.license` |

Files to produce:

- **`CONTRIBUTING.md.tpl`**: dev setup (pip install -e .), commit conventions table (feat/fix/docs/refactor/perf/test/chore/BREAKING CHANGE), PR process (one concern per PR, CI must be green, reference issue with `Closes #N`), bug reporting pointer
- **`CODE_OF_CONDUCT.md.tpl`**: Contributor Covenant v2.1 full text with `{{AUTHOR_NAME}}` as enforcement contact
- **`pull_request_template.md.tpl`**: summary field, related issue field (Closes #N), type checkboxes (bug fix, new feature, docs, refactor, other), pre-flight checklist (syntax check, conventional commit format, docs updated, no secrets)
- **`ISSUE_TEMPLATE/bug_report.md.tpl`**: name, about, labels frontmatter; fields: what happened, steps to reproduce, command and output (code block), environment (OS, Python, tool version, install method), config (YAML block), additional context
- **`ISSUE_TEMPLATE/feature_request.md.tpl`**: name, about, labels frontmatter; fields: problem this solves, proposed solution, alternatives considered, additional context
- **`workflows/ci.yml.tpl`**: trigger on push + PR to main; matrix `python-version: ["3.10", "3.11", "3.12"]`; steps: checkout, setup-python, install ruff + pip install -e ., ruff check, py_compile on all .py files, configurable import check list
- **`workflows/stale.yml.tpl`**: weekly schedule; issues stale after 60d, close after 14d; PRs stale after 30d, close after 14d; exempt labels: pinned, security, in-progress
- **`workflows/release-notes.yml.tpl`**: trigger on `v*` tag push; extract version from tag; extract CHANGELOG section for that version; create GitHub Release via `softprops/action-gh-release@v2` with body from CHANGELOG

### Step 6: Write reference docs (in `references/`)

- **`project-yaml-schema.md`**: table of every field, its type, required/optional status, default value, and which scripts consume it
- **`conventional-commits.md`**: table of commit prefix to bump type, section label, and example; note on `BREAKING CHANGE` in body; note on `!` suffix
- **`release-workflow.md`**: numbered diagram of all release steps, flags that affect each step, and what `--dry-run` skips; rollback instructions (`git tag -d vX.Y.Z && git reset --soft HEAD~1`)

### Step 7: Register skill with the framework

After all files are written, update the framework's skill registry per `_localsetup/docs/PLATFORM_REGISTRY.md`. This includes:

- Adding an entry to the skills catalog table in `_localsetup/docs/SKILLS.md`
- Deploying the skill to the platform-specific path (e.g. `.cursor/skills/localsetup-github-repo-manager/SKILL.md` for Cursor) per the platform registration instructions

---

## Acceptance criteria

All of the following must be true before the skill is marked `done`:

- [ ] `_localsetup/skills/localsetup-github-repo-manager/SKILL.md` exists and passes Agent Skills spec validation (name matches directory, description under 1024 chars, body under 500 lines)
- [ ] `project.yaml.template` contains every field listed in the schema with inline documentation comments
- [ ] All four scripts (`stamp.py`, `bump_version.py`, `check_docs.py`, `release.py`) are present and importable without error on Python 3.10
- [ ] `python scripts/stamp.py --dry-run` completes without error against a test repo containing a minimal `project.yaml`
- [ ] `python scripts/bump_version.py --dry-run` completes without error on a repo with at least one conventional commit since the last tag
- [ ] `python scripts/release.py --dry-run --allow-stale-docs` completes without error on a clean repo
- [ ] `python scripts/check_docs.py --since HEAD~1` exits 0 on a repo with no broken links, 1 on a repo with a broken link
- [ ] All template files exist in `templates/github/` with correct token names
- [ ] All three reference docs exist in `references/`
- [ ] Skill is registered in `_localsetup/docs/SKILLS.md`
- [ ] No hardcoded project names, author names, URLs, or repo paths appear anywhere in the skill
- [ ] Running `stamp.py` twice on the same file produces identical output (idempotency check)
- [ ] `ruff check scripts/` passes with no errors
- [ ] SKILL.md includes a complete "Quick start" section with the bootstrap command sequence

---

## Verification plan

1. Copy `project.yaml.template` to a scratch test repo as `project.yaml`, fill in test values
2. Run `stamp.py --dry-run` and verify the footer preview matches expected HTML structure
3. Run `stamp.py` and verify footers appear in all `stamp_targets`, sentinel comments wrap the block
4. Run `stamp.py` again and verify all statuses show `unchanged` (idempotency)
5. Make two commits with `feat:` prefix, run `bump_version.py --dry-run` and verify bump type is `minor`
6. Run `release.py --dry-run --allow-stale-docs` on the test repo; verify all 8 (or 7 with `--no-push`) steps print without error
7. Introduce a broken markdown link in a test doc; run `check_docs.py --since HEAD~1`; verify exit code 1 and correct link reported
8. Run `ruff check scripts/` and verify no lint errors

---

## Rollback plan

- The skill adds files only inside `_localsetup/skills/localsetup-github-repo-manager/` and updates `_localsetup/docs/SKILLS.md`
- No changes are made to the target repo during skill creation; all repo-level changes are user-initiated by running the scripts
- To roll back: `git revert <commit>` or `rm -rf _localsetup/skills/localsetup-github-repo-manager/` and revert the SKILLS.md entry
- Scripts themselves are non-destructive by default; `--dry-run` is available on all write operations

---

## Referenced artifacts (per GIT_TRACEABILITY.md)

| Artifact | Path | Commit |
|---|---|---|
| Working stamp.py | `maintenance/stamp.py` | `56deced` |
| Working bump_version.py | `maintenance/bump_version.py` | `56deced` |
| Working check_docs.py | `maintenance/check_docs.py` | `56deced` |
| Working release.py | `maintenance/release.py` | `56deced` |
| Working project.yaml | `project.yaml` | `56deced` |
| CI workflow | `.github/workflows/ci.yml` | `3e8e918` |
| Stale workflow | `.github/workflows/stale.yml` | `3e8e918` |
| Release notes workflow | `.github/workflows/release-notes.yml` | `3e8e918` |
| CONTRIBUTING template | `.github/CONTRIBUTING.md` | `3e8e918` |
| CODE_OF_CONDUCT | `.github/CODE_OF_CONDUCT.md` | `3e8e918` |
| Bug report template | `.github/ISSUE_TEMPLATE/bug_report.md` | `3e8e918` |
| Feature request template | `.github/ISSUE_TEMPLATE/feature_request.md` | `3e8e918` |
| PR template | `.github/pull_request_template.md` | `3e8e918` |
| Tooling policy | `_localsetup/docs/TOOLING_POLICY.md` | `56deced` |
| Input hardening standard | `_localsetup/docs/INPUT_HARDENING_STANDARD.md` | `56deced` |
| Agent Skills compliance | `_localsetup/docs/AGENT_SKILLS_COMPLIANCE.md` | `56deced` |
| Skill normalization | `_localsetup/docs/SKILL_NORMALIZATION.md` | `56deced` |
| PRD schema | `_localsetup/docs/PRD_SCHEMA_EXTERNAL_AGENT_GUIDE.md` | `56deced` |

---

## Outcome block

*(To be completed by the implementing agent after execution)*

```
branch:
commit_sha:
files_changed:
verification:
rollback_command:
```

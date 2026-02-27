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

Create a new Agent Skills-compliant framework skill that packages a complete, language-agnostic GitHub repository management and publishing automation system. The skill works with any project type: Python, TypeScript, Swift, Go, Rust, shell scripts, documentation-only repos, or anything else hosted on GitHub.

All behavior is driven by a single `project.yaml` configuration file at the repo root. The user declares their project's identity, which files hold version strings (with the regex patterns to find them), which markdown files receive copyright footers, and which source-to-doc relationships to track. No language, framework, build tool, or file path is hardcoded inside the skill.

This skill is derived from a working implementation at commit `56deced` of a reference Python repo. That implementation is generalized here into a framework primitive that is installable into any Localsetup v2 repository, regardless of what the repo contains.

---

## Background and motivation

Publishing a project to GitHub and keeping it maintained over time involves a set of tasks that most teams rebuild from scratch on every new repo: identity propagation, version bumping, CHANGELOG management, copyright footers, CI workflows, community health files, and release automation. The reference implementation solved all of these for one specific Python project. This skill extracts that solution, strips all language-specific assumptions, and makes it available as a single installable unit.

The skill covers:

- Project identity management (author, company, copyright year) propagated to any set of files via user-defined regex sync rules
- Semantic versioning driven by conventional commits, reading and writing a plain `VERSION` file
- CHANGELOG generation grouped by commit type, in Keep a Changelog format
- Copyright footer stamping across any list of markdown files
- GitHub community health files: CONTRIBUTING, CODE_OF_CONDUCT, issue templates, PR template
- GitHub Actions workflows: a language-agnostic CI placeholder, stale issue management, and automatic GitHub Release creation on tag push
- Doc staleness detection: user-declared source-to-doc map, evaluated against git-changed files
- Broken internal link scanning across declared public docs
- A single `release.py` command that runs all steps in order with dry-run support throughout

---

## Skill specification

### Skill metadata (SKILL.md frontmatter)

```yaml
name: localsetup-github-repo-manager
description: >
  Language-agnostic GitHub repository management and publishing automation.
  Manages project identity (author, company, copyright), semantic versioning
  from conventional commits, CHANGELOG generation, copyright footer stamping,
  GitHub community health files, and CI/CD workflows. All behavior is driven
  by project.yaml with no hardcoded language, framework, or file paths. Works
  with Python, TypeScript, Swift, Go, Rust, or any other project type. Use
  when setting up a new GitHub repo, cutting a release, updating project
  identity, or adding community health files and CI to an existing project.
metadata:
  version: "1.0"
compatibility: >
  The skill's management tooling requires Python >= 3.10 and PyYAML >= 6.0
  (the managed repo itself may be any language). Git CLI must be present.
  All scripts follow framework TOOLING_POLICY: Python-only, no shell scripts.
```

---

## Deliverables

The agent implementing this PRD produces the following file tree inside `_localsetup/skills/localsetup-github-repo-manager/`:

```
localsetup-github-repo-manager/
├── SKILL.md
├── project.yaml.template
├── scripts/
│   ├── stamp.py          # Footer stamper + identity syncer (config-driven)
│   ├── bump_version.py   # Semver bumper from conventional commits
│   ├── check_docs.py     # Doc staleness + broken link checker
│   └── release.py        # Full release workflow orchestrator
├── templates/
│   ├── github/
│   │   ├── CONTRIBUTING.md.tpl
│   │   ├── CODE_OF_CONDUCT.md.tpl
│   │   ├── pull_request_template.md.tpl
│   │   ├── ISSUE_TEMPLATE/
│   │   │   ├── bug_report.md.tpl
│   │   │   └── feature_request.md.tpl
│   │   └── workflows/
│   │       ├── ci.yml.tpl             # Language-agnostic CI placeholder
│   │       ├── stale.yml.tpl
│   │       └── release-notes.yml.tpl
│   ├── CHANGELOG.md.tpl
│   └── LICENSE.mit.tpl
└── references/
    ├── project-yaml-schema.md
    ├── conventional-commits.md
    └── release-workflow.md
```

---

## Implementation steps

### Step 1: Bootstrap skill directory

1. Create `_localsetup/skills/localsetup-github-repo-manager/` with the directory structure above.
2. Verify the directory name matches the `name` field in SKILL.md frontmatter exactly.
3. Do not modify the target repo during skill creation. All repo-level changes are applied by the user after installation.

### Step 2: Write SKILL.md

Produce a complete SKILL.md satisfying the Agent Skills spec (`_localsetup/docs/AGENT_SKILLS_COMPLIANCE.md`, `_localsetup/docs/SKILL_NORMALIZATION.md`):

- Frontmatter: `name`, `description` (under 1024 chars), `metadata.version`, `compatibility`
- Body structured as: Purpose, Prerequisites, Installation, Workflows, Configuration reference
- Keep body under 500 lines
- Language-neutral throughout: no mention of pip, npm, cargo, swift, ruff, or any build tool
- Script invocations shown as `python _localsetup/skills/localsetup-github-repo-manager/scripts/<name>.py`

The SKILL.md body must cover four workflows:

**Identity workflow.** User edits `project.yaml`, runs `stamp.py`. Every doc listed in `stamp_targets` gets a refreshed footer. Every file listed in `version_sync.code_files` gets its identity fields updated via the regex rules in `project.yaml`. One command, idempotent.

**Release workflow.** User runs `release.py`. Steps execute in order: pre-flight, doc validation, stamp, version bump and CHANGELOG, commit, tag, optional push. Supports `--dry-run`, `--no-push`, `--allow-stale-docs`, `--major`/`--minor`/`--patch`.

**Doc check workflow.** User runs `check_docs.py`. Reports broken internal links and flags docs whose paired source files have changed since a given git ref.

**Bootstrap workflow.** User copies `project.yaml.template` to repo root, fills in values, copies `.github/` templates (substituting tokens), optionally copies `CHANGELOG.md.tpl` and `LICENSE.mit.tpl`. SKILL.md provides the exact commands.

### Step 3: Write `project.yaml.template`

Every field must have an inline comment stating its purpose and which scripts consume it. The template must contain no language-specific defaults or examples.

```yaml
# project.yaml
# Single source of truth for project identity and repo management configuration.
# Copy to your repo root. Fill in all fields. Then run:
#   python _localsetup/skills/localsetup-github-repo-manager/scripts/stamp.py

project:
  name: ""          # Short name used in docs and templates  [stamp, release]
  description: ""   # One-line description                   [templates]
  repository: ""    # Full GitHub URL: https://github.com/OWNER/REPO  [stamp, release]

author:
  name: ""          # Full name of the primary author        [stamp, templates, LICENSE]
  github: ""        # GitHub username (no @)                 [templates]
  email: ""         # Optional contact email                 [templates; leave blank to omit]

company:
  name: ""          # Company or organization (appears linked in footer)  [stamp]
  url: ""           # Company website URL                                 [stamp]

copyright:
  year: ""          # Copyright year or range, e.g. 2026 or 2024-2026   [stamp, LICENSE]
  license: MIT      # License identifier shown in footer                 [stamp, templates]

# ---------------------------------------------------------------------------
# Footer: markdown files that receive the centered copyright footer block.
# Paths relative to repo root. Add or remove to match your actual layout.
# stamp.py reads this list. Safe to leave a path in the list even if the
# file does not yet exist; stamp.py skips missing files with status [-].
# ---------------------------------------------------------------------------
stamp_targets:
  - README.md
  - CHANGELOG.md
  - .github/CONTRIBUTING.md
  - .github/CODE_OF_CONDUCT.md
  # Add any other public markdown files here:
  # - docs/architecture.md
  # - docs/api.md

# ---------------------------------------------------------------------------
# Version sync: files outside VERSION that embed the version string.
# stamp.py and bump_version.py use this list to keep version strings current.
# Each entry has:
#   path    - path relative to repo root
#   pattern - Python regex with one capture group before and one after the version
#   replace - replacement template; use \g<1> and \g<2> for the capture groups
#
# Examples for common patterns across languages:
#   Python __init__.py:  pattern: '(__version__\s*=\s*")[^"]+(")'
#   package.json:        pattern: '("version":\s*")[^"]+(")'
#   Swift Package.swift: pattern: '(version:\s*")[^"]+(")'
#   Cargo.toml:          pattern: '(^version\s*=\s*")[^"]+(")'
#   README badge:        pattern: '(!\[version\]\([^)]+/v)[^)]+(\))'
#
# Leave this list empty if VERSION is your only version file.
# ---------------------------------------------------------------------------
version_sync:
  code_files: []
  # - path: "src/index.ts"
  #   pattern: '(export const VERSION = ")[^"]+(")'
  #   replace: '\g<1>{version}\g<2>'
  # - path: "package.json"
  #   pattern: '("version":\s*")[^"]+(")'
  #   replace: '\g<1>{version}\g<2>'

# ---------------------------------------------------------------------------
# Doc staleness map: when a source file changes, which docs should be reviewed?
# check_docs.py uses this map. Each entry has:
#   sources - list of file globs (relative to repo root)
#   docs    - list of doc paths that cover those sources
#   reason  - human-readable string explaining the relationship
#
# Populate this to match your project's actual structure.
# Leave empty to skip staleness checking (link checking still runs).
# ---------------------------------------------------------------------------
doc_map: []
# - sources: ["src/**/*.ts"]
#   docs: ["README.md", "docs/api.md"]
#   reason: "Source API changed"
# - sources: ["Cargo.toml", "src/lib.rs"]
#   docs: ["README.md", "docs/architecture.md"]
#   reason: "Core library changed"

# ---------------------------------------------------------------------------
# Public docs: files always checked for broken internal links.
# ---------------------------------------------------------------------------
public_docs:
  - README.md
  - CHANGELOG.md
  - .github/CONTRIBUTING.md
  # Add any other published markdown files:
  # - docs/api.md
```

### Step 4: Write Python scripts

All scripts follow the framework standard (`_localsetup/docs/TOOLING_POLICY.md`, `_localsetup/docs/INPUT_HARDENING_STANDARD.md`):

- Python 3.10+ only. PyYAML for all YAML. `require_deps()` from `lib.deps` at startup.
- Hostile-by-default: validate all CLI args, config fields, and file paths; emit actionable errors to stderr with field name and context.
- No silent failure on critical paths.
- `--dry-run` on every script that modifies files or runs git commands.
- All scripts importable as modules (no bare module-level side effects outside `if __name__ == "__main__"`).
- No hardcoded file names, language names, or tool names anywhere in script logic.

#### `stamp.py`

Responsibilities:

1. Load and validate `project.yaml` (path via `--config`, default `./project.yaml`). Required fields: `author.name`, `company.name`, `company.url`, `copyright.year`, `project.repository`. Emit per-field errors to stderr if missing.
2. Build footer HTML: `<br><br>` separator, `<p align="center">`, author name on line 1, `&copy; YEAR <a href="COMPANY_URL">COMPANY_NAME</a> &mdash; <a href="REPO_URL/blob/main/LICENSE">LICENSE License</a>` on line 2, closing `</p>`.
3. Wrap footer in sentinel comments `<!-- project-footer:start -->` / `<!-- project-footer:end -->` for idempotent replacement.
4. For each path in `stamp_targets`: strip existing sentinel block, append `\n\n` + footer block. Skip missing files with status `[-]`.
5. For each entry in `version_sync.code_files`: apply the user-supplied `pattern` and `replace` fields to sync the author/identity string. The replace template is not constrained to a particular language; it is whatever the user configured. Skip entries whose `path` does not exist.
6. Update `LICENSE` copyright line by matching `Copyright (c) YEAR NAME` pattern if LICENSE exists.
7. Print per-file status: `[+] stamped`, `[~] updated`, `[=] unchanged`, `[-] skipped (not found)`, `[!] no-match`.

Flags: `--dry-run`, `--no-docs` (skip markdown), `--no-code` (skip code files and LICENSE), `--config PATH`.

#### `bump_version.py`

Responsibilities:

1. Read `VERSION` file from repo root.
2. Get commits since the last git tag. If no tag exists, use the root commit as the base (not `HEAD`, which would scan the entire history and incorrectly classify a repo's full history as "unreleased").
3. Classify commits by conventional commit prefix to determine bump type:
   - `BREAKING CHANGE:` in message body or `type!:` prefix: major
   - `feat:` or `feat(scope):`: minor
   - All other recognized prefixes: patch
4. Write incremented version to `VERSION`.
5. Sync version string to each entry in `version_sync.code_files` using the user-supplied `pattern` and `replace` fields. Each pattern applies a regex substitution; the script does not know or care what language the file is.
6. Prepend a new dated section to `CHANGELOG.md` via `generate_changelog_entry()`:
   - Groups commits by section label: Added (feat), Fixed (fix), Changed (perf/refactor), Documentation (docs), Maintenance (chore/test/ci/build/style)
   - Skips version bump commits (messages matching `bump version to`)
   - Updates the `[Unreleased]` comparison link and appends the new version comparison link at the bottom of CHANGELOG
7. Exportable functions: `read_version()`, `write_version()`, `parse_semver()`, `bump()`, `get_commits_since_last_tag()`, `determine_bump_type()`, `generate_changelog_entry()`, `prepend_changelog()`, `VERSION_SYNC_TARGETS` (built from config).

Flags: `--dry-run`, `--major`, `--minor`, `--patch`, `--config PATH`.

#### `check_docs.py`

Responsibilities:

1. Accept `--since REF` (default `HEAD~1`; `last-tag` resolves to the most recent git tag or falls back to `HEAD~1`).
2. Run `git diff --name-only SINCE HEAD` to get changed files.
3. Load `doc_map` from `project.yaml`. For each entry whose `sources` globs match a changed file, flag the paired `docs` for review with the `reason` string.
4. Load `public_docs` from `project.yaml`. For each file, scan for broken internal markdown links (`[text](path)` where path is not `http://`, not `https://`, not `#`, and the resolved file does not exist on disk).
5. Return a `DocCheckResult` dataclass: `changed_sources`, `docs_to_review` (list of `(doc, reason)`), `broken_links` (list of `(doc, link)`).
6. Exit code 0 if clean, 1 if any issues.

Flags: `--since REF`, `--verbose`, `--config PATH`.

#### `release.py`

Orchestrates the full release in order. Each step prints `[N/TOTAL] Label`. Total adjusts automatically when `--no-push` is set.

Steps:

1. Pre-flight: working tree clean (unless `--allow-dirty`), on release branch (configurable, default `main`), remote reachable (unless `--no-push`).
2. Doc link check: call `check_docs.run()`; abort if broken links found; flag stale docs unless `--allow-stale-docs`.
3. Determine bump: read commits, classify, compute new version; verify tag does not already exist.
4. Confirm: interactive `[y/N]` prompt showing current version and new version. Skipped under `--dry-run`.
5. Stamp: run `stamp.stamp_docs()` and `stamp.sync_code_files()` to refresh footers and identity.
6. Bump and sync: run `bump_version.run()` to write `VERSION`, sync all `version_sync.code_files`, prepend CHANGELOG entry.
7. Commit: stage `VERSION`, `CHANGELOG.md`, `LICENSE`, all `stamp_targets`, all `version_sync.code_files` paths. Commit with message `chore: bump version to X.Y.Z`.
8. Tag: create annotated git tag `vX.Y.Z` with message `Release vX.Y.Z`.
9. Push (optional): push branch and tag to origin.

Flags: `--dry-run`, `--no-push`, `--allow-dirty`, `--allow-stale-docs`, `--major`, `--minor`, `--patch`, `--since REF`, `--branch NAME`, `--config PATH`.

### Step 5: Write GitHub template files

All `.tpl` files use `{{TOKEN}}` substitution. The bootstrap step renders them by reading `project.yaml` and replacing tokens before writing to the target repo. Tokens:

| Token | Source field |
|---|---|
| `{{PROJECT_NAME}}` | `project.name` |
| `{{REPO_URL}}` | `project.repository` |
| `{{AUTHOR_NAME}}` | `author.name` |
| `{{AUTHOR_GITHUB}}` | `author.github` |
| `{{COMPANY_NAME}}` | `company.name` |
| `{{COMPANY_URL}}` | `company.url` |
| `{{COPYRIGHT_YEAR}}` | `copyright.year` |
| `{{LICENSE}}` | `copyright.license` |

Files to produce and their required content:

**`CONTRIBUTING.md.tpl`**

Sections: how to set up a development environment (generic: "clone the repo, install dependencies using your project's package manager"), the conventional commit table (all prefixes and bump types), PR process (one concern per PR, CI must pass, reference issue with `Closes #N`), how to report bugs (link to bug report template).

No mention of any specific language, build tool, package manager, or install command. Use language-neutral phrasing such as "install dependencies per your project's setup instructions."

**`CODE_OF_CONDUCT.md.tpl`**

Full Contributor Covenant v2.1 text. `{{AUTHOR_NAME}}` appears as the enforcement contact. No other customization.

**`pull_request_template.md.tpl`**

Fields: summary (free text), related issue (`Closes #N` or `No related issue`), type checkboxes (Bug fix, New feature, Documentation, Refactor, Other). Pre-flight checklist: code builds and tests pass per project's standard process, conventional commit format used, docs updated if behavior changed, no secrets or PII included.

No language-specific checklist items.

**`ISSUE_TEMPLATE/bug_report.md.tpl`**

Frontmatter: `name`, `about`, `labels: bug`. Sections: what happened (expected vs actual), steps to reproduce (numbered list), command and output (fenced code block), environment (OS, tool version, install method - all generic), configuration (fenced block, "remove sensitive values"), additional context.

Environment section asks for "tool version" and "install method" generically, not Python version or pip.

**`ISSUE_TEMPLATE/feature_request.md.tpl`**

Frontmatter: `name`, `about`, `labels: enhancement`. Sections: problem this solves, proposed solution, alternatives considered, additional context.

**`workflows/ci.yml.tpl`**

Trigger: push and pull_request targeting main branch. Single job named `build-and-test`. Steps: checkout (actions/checkout@v4), then a clearly marked placeholder block instructing the user to replace it with their language's setup and test steps. The placeholder comment reads:

```yaml
# TODO: Replace the steps below with your project's build and test commands.
# Examples:
#   Python:     pip install -e . && pytest
#   Node/TS:    npm ci && npm test
#   Go:         go test ./...
#   Rust:       cargo test
#   Swift:      swift test
#   Other:      adapt to your build system
- name: Build and test
  run: echo "Replace this step with your build and test commands"
```

The workflow file is otherwise complete and functional (checkout, correct trigger syntax, job definition). The user only needs to replace the placeholder run command.

**`workflows/stale.yml.tpl`**

Schedule: weekly (Monday 09:00 UTC) plus `workflow_dispatch`. Uses `actions/stale@v9`. Issues: stale after 60 days, close after 14 more. PRs: stale after 30 days, close after 14 more. Exempt labels: `pinned`, `security`, `in-progress`. All label names and messages use `{{PROJECT_NAME}}` where contextual.

**`workflows/release-notes.yml.tpl`**

Trigger: push of tags matching `v*`. Steps: checkout (full history, `fetch-depth: 0`), extract version from tag, extract matching CHANGELOG section via `awk`, create GitHub Release via `softprops/action-gh-release@v2` with body from CHANGELOG section. Permissions: `contents: write`. No language-specific steps.

**`CHANGELOG.md.tpl`**

Keep a Changelog format seed with `[Unreleased]` section, one seeded `[{{VERSION}}]` entry placeholder, and comparison links at the bottom. Footer not included (stamp.py handles that separately).

**`LICENSE.mit.tpl`**

Standard MIT License text with `{{COPYRIGHT_YEAR}}` and `{{AUTHOR_NAME}}, {{COMPANY_NAME}}` in the copyright line.

### Step 6: Write reference docs

**`references/project-yaml-schema.md`**

Table listing every field in `project.yaml.template`: field path (dotted), type, required/optional, default, and which scripts consume it. A second table lists the `version_sync.code_files` entry schema with fields `path`, `pattern`, `replace` and example rows for Python, Node/TypeScript, Go, Rust, and Swift showing what the pattern and replace look like for each. A third table covers `doc_map` entry fields.

**`references/conventional-commits.md`**

Table of commit prefix, bump type triggered, CHANGELOG section it appears under, and one example commit message per prefix. Notes on `BREAKING CHANGE:` in the message body and on the `!` suffix (e.g. `feat!:`). Does not reference any specific language.

**`references/release-workflow.md`**

Numbered list of all release steps matching `release.py`'s step counter. For each step: what it does, which flags affect it, and what `--dry-run` skips. Rollback instructions: `git tag -d vX.Y.Z && git reset --soft HEAD~1 && git push origin --delete vX.Y.Z` with a warning to only run this before the release is announced. Step count matrix showing total steps with and without `--no-push`.

### Step 7: Register the skill

After all files are written, update the framework skill registry per `_localsetup/docs/PLATFORM_REGISTRY.md`:

- Add entry to the skills catalog table in `_localsetup/docs/SKILLS.md`
- Deploy to the platform-specific path (e.g. `.cursor/skills/localsetup-github-repo-manager/SKILL.md` for Cursor) per platform registration instructions

---

## Acceptance criteria

- [ ] SKILL.md exists, passes Agent Skills spec validation, description is under 1024 chars, body under 500 lines
- [ ] SKILL.md contains no references to any specific programming language, build tool, or package manager
- [ ] `project.yaml.template` contains all fields defined in this PRD with inline comments, including `version_sync.code_files`, `doc_map`, and `public_docs`
- [ ] All four scripts are present and importable without error on Python 3.10
- [ ] No script contains hardcoded filenames like `setup.py`, `package.json`, `Cargo.toml`, `__init__.py`, or any other language-specific path
- [ ] `stamp.py --dry-run` completes without error against a minimal `project.yaml` with empty `version_sync.code_files`
- [ ] `stamp.py` run twice on the same files produces identical output (idempotency)
- [ ] `bump_version.py --dry-run` completes without error on a repo with at least one conventional commit
- [ ] `release.py --dry-run --allow-stale-docs` completes without error on a clean repo
- [ ] `check_docs.py --since HEAD~1` exits 0 on a repo with no broken links, 1 on a repo with one broken link
- [ ] CI workflow template contains a clearly marked TODO placeholder, not any specific build command
- [ ] CONTRIBUTING template contains no language-specific setup instructions
- [ ] Bug report template asks for "tool version" and "OS version" generically, not "Python version"
- [ ] `version_sync` example rows in the reference doc cover at least: Python, Node/TypeScript, Go, Rust, Swift
- [ ] All template tokens use the `{{TOKEN}}` format consistently
- [ ] All three reference docs exist in `references/`
- [ ] Skill is registered in `_localsetup/docs/SKILLS.md`
- [ ] `ruff check scripts/` passes with no errors

---

## Verification plan

1. Copy `project.yaml.template` to a scratch repo as `project.yaml`; fill in identity fields; leave `version_sync.code_files` empty; run `stamp.py --dry-run` and verify footer HTML preview is correct
2. Run `stamp.py`; verify sentinels wrap footer in every stamp target; run again and verify all `[=] unchanged`
3. Add a `version_sync.code_files` entry pointing to a test file with a matching pattern; run `stamp.py` and verify the field updates; run again and verify `[=] unchanged`
4. Create two commits with `feat:` prefix; run `bump_version.py --dry-run`; verify bump type is `minor`
5. Run `release.py --dry-run --allow-stale-docs`; verify all steps print without error; verify step counter is correct
6. Introduce a broken markdown link in a test doc; run `check_docs.py --since HEAD~1`; verify exit 1 and the broken link is named
7. Open `ci.yml.tpl` and verify the TODO placeholder is present and the surrounding YAML is syntactically valid
8. Open `CONTRIBUTING.md.tpl` and verify no language-specific install commands appear
9. Run `ruff check scripts/`; verify no errors

---

## Rollback plan

- The skill adds files only inside `_localsetup/skills/localsetup-github-repo-manager/` and updates `_localsetup/docs/SKILLS.md`
- No changes are made to the target repo during skill creation; all repo-level changes are user-initiated
- Rollback: `git revert <commit>` or `rm -rf _localsetup/skills/localsetup-github-repo-manager/` and revert the SKILLS.md line
- All scripts are non-destructive by default; `--dry-run` is available on every write operation

---

## Referenced artifacts (per GIT_TRACEABILITY.md)

| Artifact | Path | Commit |
|---|---|---|
| Reference stamp.py | `maintenance/stamp.py` | `56deced` |
| Reference bump_version.py | `maintenance/bump_version.py` | `56deced` |
| Reference check_docs.py | `maintenance/check_docs.py` | `56deced` |
| Reference release.py | `maintenance/release.py` | `56deced` |
| Reference project.yaml | `project.yaml` | `56deced` |
| CI workflow (reference) | `.github/workflows/ci.yml` | `3e8e918` |
| Stale workflow (reference) | `.github/workflows/stale.yml` | `3e8e918` |
| Release notes workflow (reference) | `.github/workflows/release-notes.yml` | `3e8e918` |
| CONTRIBUTING (reference) | `.github/CONTRIBUTING.md` | `3e8e918` |
| CODE_OF_CONDUCT (reference) | `.github/CODE_OF_CONDUCT.md` | `3e8e918` |
| Bug report template (reference) | `.github/ISSUE_TEMPLATE/bug_report.md` | `3e8e918` |
| Feature request template (reference) | `.github/ISSUE_TEMPLATE/feature_request.md` | `3e8e918` |
| PR template (reference) | `.github/pull_request_template.md` | `3e8e918` |
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
